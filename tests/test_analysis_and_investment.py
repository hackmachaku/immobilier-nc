import pytest
from pathlib import Path

from src.models.listing import RawListing, Commune, PropertyType
from src.storage.database import PropertyDatabase
from src.ingestion.collector import IngestionPipeline
from src.ingestion.sample_generator import get_pilot_dataset
from src.analysis.market_stats import MarketAnalytics
from src.analysis.geo_map import GrandNoumeaMapGenerator
from src.investment.models import InvestmentRequest
from src.investment.calculator import InvestmentCalculator


@pytest.fixture
def populated_db(tmp_path):
    db_file = tmp_path / "test_populated.duckdb"
    db = PropertyDatabase(db_file)
    pipeline = IngestionPipeline(db)
    pipeline.process_and_store(get_pilot_dataset(), batch_tag="test_suite")
    return db


def test_market_distributions(populated_db):
    analytics = MarketAnalytics(populated_db)
    dist_df = analytics.get_price_distributions()

    assert not dist_df.empty
    assert "p25_m2_xpf" in dist_df.columns
    assert "median_m2_xpf" in dist_df.columns
    assert "p75_m2_xpf" in dist_df.columns

    # Vérification que P25 <= Médiane <= P75
    for _, row in dist_df.iterrows():
        assert row["p25_m2_xpf"] <= row["median_m2_xpf"] <= row["p75_m2_xpf"]


def test_opportunity_detection(populated_db):
    analytics = MarketAnalytics(populated_db)
    opps = analytics.detect_market_opportunities(min_discount_pct=5.0)

    # Doit identifier au moins une opportunité avec décote positive
    assert isinstance(opps, list)
    for op in opps:
        assert op["decote_pct"] >= 5.0
        assert op["gain_potentiel_xpf"] > 0
        assert op["valeur_estimee_xpf"] > op["prix_affiche_xpf"]


def test_interactive_map_generation(populated_db, tmp_path):
    map_gen = GrandNoumeaMapGenerator(populated_db)
    target_html = tmp_path / "test_carte.html"
    result_path = map_gen.generate_map(target_html)

    assert result_path.exists()
    assert result_path.stat().st_size > 1000

    content = result_path.read_text(encoding="utf-8")
    assert "Anse Vata" in content
    assert "Savannah" in content
    assert "Boulari" in content


def test_investment_calculator_mortgage():
    calc = InvestmentCalculator()
    # Emprunt de 15 000 000 F CFP à 4.2% sur 20 ans
    mensualite, cout_total, interets = calc.calculate_mortgage(
        capital=15_000_000,
        taux_annuel_pct=4.2,
        duree_annees=20,
    )
    # Formule théorique : Mensualité ~ 92 485 F CFP / mois
    assert 92_000 <= mensualite <= 93_000
    assert cout_total == mensualite * 240
    assert interets == cout_total - 15_000_000


def test_full_investment_simulation():
    calc = InvestmentCalculator()

    # Cas d'un appartement F2 à Koutio (13,5M F CFP, loyer 85 000 F/mois)
    req = InvestmentRequest(
        nom_projet="Test F2 Koutio Dumbéa",
        prix_acquisition_xpf=13_500_000,
        frais_notaire_taux=0.08,
        apport_personnel_xpf=1_500_000,
        taux_emprunt_annuel_pct=4.2,
        duree_emprunt_annees=20,
        loyer_mensuel_xpf=85_000,
        taux_vacance_locative_pct=5.0,
        charges_copro_mensuelles_non_recup_xpf=5_000,
        taxe_fonciere_annuelle_xpf=60_000,
        assurance_pno_annuelle_xpf=35_000,
        frais_gestion_agence_pct=7.0,
        inclure_tgc_gestion=True,
    )

    res = calc.simulate(req)

    # Vérifications de cohérence financière
    assert res.frais_notaire_xpf == int(13_500_000 * 0.08)
    assert res.cout_total_projet_xpf > 13_500_000
    assert res.montant_emprunte_xpf == res.cout_total_projet_xpf - 1_500_000
    assert res.rendement_locatif_brut_pct > 7.0
    assert res.rendement_locatif_net_charges_pct >= 4.5
    assert res.loyer_annuel_encaisse_xpf == int(85_000 * 12 * 0.95)

    # Stress-tests
    assert "HAUSSE_TAUX_PLUS_1" in res.stress_tests
    assert "VACANCE_DOUBLEE" in res.stress_tests
    assert "BAISSE_LOYER_10" in res.stress_tests
    assert res.stress_tests["HAUSSE_TAUX_PLUS_1"].cash_flow_mensuel_xpf < res.cash_flow_mensuel_net_xpf
