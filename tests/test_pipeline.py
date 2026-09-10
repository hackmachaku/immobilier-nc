import pytest
from src.models.listing import RawListing, TransactionType, PropertyType, Commune
from src.reference.geo import GeoReferential
from src.processing.cleaner import ListingCleaner
from src.processing.enricher import ListingEnricher
from src.storage.database import PropertyDatabase


@pytest.fixture
def geo_ref():
    return GeoReferential()


@pytest.fixture
def cleaner(geo_ref):
    return ListingCleaner(geo_ref)


@pytest.fixture
def enricher(geo_ref):
    return ListingEnricher(geo_ref)


def test_geo_referential_matching(geo_ref):
    commune, quartier, info = geo_ref.find_location("Superbe appartement à l'Anse Vata proche plage")
    assert commune == Commune.NOUMEA
    assert quartier == "Anse Vata"
    assert info is not None
    assert info["standing"] == "Premium"

    commune, quartier, _ = geo_ref.find_location("Villa contemporaine Savannah Païta")
    assert commune == Commune.PAITA
    assert quartier == "Savannah"

    commune, quartier, _ = geo_ref.find_location("Appartement à Koutio Dumbéa")
    assert commune == Commune.DUMBEA
    assert quartier == "Koutio"

    commune, quartier, _ = geo_ref.find_location("Maison Robinson Mont-Dore")
    assert commune == Commune.MONT_DORE
    assert quartier == "Robinson"


def test_price_cleaner(cleaner):
    # Format standard
    assert cleaner.parse_price("48 500 000 F") == 48_500_000
    assert cleaner.parse_price("18.900.000 XPF") == 18_900_000

    # Format Millions de Francs (MF)
    assert cleaner.parse_price("89 MF") == 89_000_000
    assert cleaner.parse_price("38,5 MF") == 38_500_000

    # Format Loyer mensuel
    assert cleaner.parse_price("135 000 F/mois") == 135_000


def test_surface_cleaner(cleaner):
    # Surface habitable standard
    hab, terrain, terrasse = cleaner.parse_surface("82 m²", "varangue couverte de 24 m²")
    assert hab == 82.0
    assert terrasse == 24.0

    # Surface terrain en ares (spécificité calédonienne : 7 ares 50 = 750 m²)
    hab, terrain, _ = cleaner.parse_surface("175 m²", "Terrain plat de 7 ares 50")
    assert hab == 175.0
    assert terrain == 750.0


def test_enricher_attributes(cleaner, enricher):
    raw = RawListing(
        source="test",
        source_id="1",
        url="http://example.com/1",
        title="Appartement F3 avec vue mer panoramique Anse Vata",
        description="Résidence haut de gamme sécurisée avec digicode, piscine commune et climatisation complète. Terrasse de 20 m².",
        raw_price="55 000 000 F",
        raw_surface="90 m²",
        raw_location="Anse Vata, Nouméa",
    )
    cleaned = cleaner.clean(raw)
    assert cleaned is not None
    enriched = enricher.enrich(cleaned)

    assert enriched.has_sea_view is True
    assert enriched.has_pool is True
    assert enriched.has_air_conditioning is True
    assert enriched.is_secured is True
    assert enriched.prix_m2_habitable_xpf == round(55_000_000 / 90.0, 2)
    assert enriched.price_eur > 0


def test_duckdb_storage(tmp_path, cleaner, enricher):
    test_db_path = tmp_path / "test_immo.duckdb"
    db = PropertyDatabase(test_db_path)

    raw = RawListing(
        source="test",
        source_id="test_100",
        url="http://example.com/test",
        title="Villa F4 Koutio Dumbéa",
        description="Belle villa avec terrasse",
        raw_price="28 000 000 F",
        raw_surface="95 m²",
        raw_rooms="F4",
        raw_location="Koutio, Dumbéa",
    )
    cleaned = enricher.enrich(cleaner.clean(raw))
    db.upsert_listings([cleaned])

    summary = db.get_market_summary()
    assert not summary.empty
    assert summary.iloc[0]["commune"] == "DUMBEA"
    assert summary.iloc[0]["quartier"] == "Koutio"
    assert summary.iloc[0]["prix_median_xpf"] == 28_000_000


def test_rental_price_parsing_and_differentiation(cleaner):
    from src.ingestion.live_scraper import LiveNCScraper
    scraper = LiveNCScraper()

    # 1. Test annonce de location (ex: Dock à Ducos avec loyer de 270 000 F CFP)
    rental_item = {
        "id": "506872",
        "deal_type": "location",
        "price": 270000,
        "home_size": "226.0",
        "property_type": "dock",
        "locality": {"name": "nouméa", "children": {"name": "ducos"}},
        "description": "LOCATION DOCK A DUCOS. Loyer 270 000 fcfp.",
        "photos": []
    }
    raw_loc = scraper.parse_item_to_raw_listing(rental_item)
    assert raw_loc is not None
    assert raw_loc.transaction_type_declared == "Location"
    assert "270000" in raw_loc.raw_price
    assert "270000000" not in raw_loc.raw_price

    cleaned_loc = cleaner.clean(raw_loc)
    assert cleaned_loc is not None
    assert cleaned_loc.transaction_type == TransactionType.LOCATION
    assert cleaned_loc.price_xpf == 270_000
    assert cleaned_loc.prix_m2_habitable_xpf == round(270_000 / 226.0, 2)

    # 2. Test annonce de vente (ex: Villa à 22 Millions)
    sale_item = {
        "id": "463413",
        "deal_type": "vente",
        "price": 22,
        "home_size": "92.0",
        "property_type": "maison",
        "locality": {"name": "dumbéa", "children": {"name": "koutio"}},
        "description": "Belle villa F4 à vendre.",
        "photos": []
    }
    raw_sale = scraper.parse_item_to_raw_listing(sale_item)
    assert raw_sale is not None
    assert raw_sale.transaction_type_declared == "Vente"
    assert raw_sale.raw_price == "22000000 F CFP"

    cleaned_sale = cleaner.clean(raw_sale)
    assert cleaned_sale is not None
    assert cleaned_sale.transaction_type == TransactionType.VENTE
    assert cleaned_sale.price_xpf == 22_000_000
    assert cleaned_sale.prix_m2_habitable_xpf == round(22_000_000 / 92.0, 2)

