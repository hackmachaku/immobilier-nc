import pytest
from src.models.listing import Commune, PropertyType
from src.valuation.avm import HedonicValuationEngine, PropertyValuationRequest


@pytest.fixture
def engine():
    return HedonicValuationEngine()


def test_valuation_appartement_anse_vata(engine):
    req = PropertyValuationRequest(
        commune=Commune.NOUMEA,
        quartier="Anse Vata",
        property_type=PropertyType.APPARTEMENT,
        surface_habitable_m2=85.0,
        surface_varangue_m2=20.0,
        vue_mer="BELLE_VUE",
        etage="DERNIER_ETAGE_ATTIQUE",
        etat_bien="RENOVE_HAUT_STANDING",
        parking_type="GARAGE_FERME_BOX",
        nb_parkings=2,
    )
    res = engine.evaluate(req)

    # Vérifications de cohérence
    assert res.valeur_centrale_xpf > 50_000_000
    assert res.fourchette_basse_xpf < res.valeur_centrale_xpf < res.fourchette_haute_xpf
    assert res.loyer_mensuel_estime_xpf > 200_000
    assert 4.5 <= res.rendement_locatif_brut_pct <= 6.5
    assert res.indice_confiance == "ÉLEVÉ"

    # Vérification des ajustements
    categories = [adj.category for adj in res.ajustements]
    assert "BASE" in categories
    assert "VUE" in categories
    assert "ETAGE" in categories
    assert "ETAT" in categories
    assert "EXTERIEURS" in categories
    assert "DEPENDANCES" in categories


def test_valuation_villa_savannah(engine):
    req = PropertyValuationRequest(
        commune=Commune.PAITA,
        quartier="Savannah",
        property_type=PropertyType.MAISON_VILLA,
        surface_habitable_m2=180.0,
        surface_varangue_m2=40.0,
        surface_deck_m2=50.0,
        surface_terrain_m2=1800.0,  # 18 ares
        vue_mer="APERÇU",
        etat_bien="BON_ETAT",
        piscine="MACONNEE_LAGON",
        parking_type="CARPORT_COUVERT",
        nb_parkings=2,
    )
    res = engine.evaluate(req)

    assert res.valeur_centrale_xpf > 70_000_000
    assert res.fourchette_basse_xpf < res.valeur_centrale_xpf < res.fourchette_haute_xpf
    assert res.rendement_locatif_brut_pct > 5.0

    # Présence valorisation foncière et piscine
    labels = [adj.label for adj in res.ajustements]
    assert any("Foncier résiduel" in l for l in labels)
    assert any("Piscine" in l for l in labels)
    assert any("Deck" in l for l in labels)


def test_valuation_dumbea_koutio_f2(engine):
    req = PropertyValuationRequest(
        commune=Commune.DUMBEA,
        quartier="Koutio",
        property_type=PropertyType.APPARTEMENT,
        surface_habitable_m2=45.0,
        surface_varangue_m2=8.0,
        vue_mer="AUCUNE",
        etage="INTERMEDIAIRE",
        etat_bien="BON_ETAT",
        parking_type="PARKING_EXT_SECURISE",
        nb_parkings=1,
    )
    res = engine.evaluate(req)

    # Appartement F2 Koutio typique ~ 12M à 16M F CFP
    assert 12_000_000 <= res.valeur_centrale_xpf <= 18_000_000
    assert res.rendement_locatif_brut_pct >= 6.0


def test_conjoncture_mont_dore_sud(engine):
    req = PropertyValuationRequest(
        commune=Commune.MONT_DORE,
        quartier="Vallon-Dore",
        property_type=PropertyType.MAISON_VILLA,
        surface_habitable_m2=120.0,
        surface_terrain_m2=1000.0,
        etat_bien="BON_ETAT",
    )
    res = engine.evaluate(req)

    # Le facteur de conjoncture pour le Mont-Dore Sud doit refléter la décote d'accessibilité
    assert res.facteur_conjoncture < 0.85
    assert any("conjoncture" in adj.label.lower() for adj in res.ajustements)
