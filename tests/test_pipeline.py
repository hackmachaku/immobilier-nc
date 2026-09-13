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


def test_multi_photos_pipeline(tmp_path, cleaner):
    import json
    from src.ingestion.live_scraper import LiveNCScraper
    scraper = LiveNCScraper()

    # Annonce avec 3 photos
    item_multi = {
        "id": "777888",
        "deal_type": "vente",
        "price": 35,
        "home_size": "100.0",
        "property_type": "appartement",
        "locality": {"name": "nouméa", "children": {"name": "anse vata"}},
        "description": "Superbe F3 avec vue mer.",
        "photos": [
            {"picture": "https://gestion.immobilier.nc/photos/img1.jpg"},
            {"picture": "https://gestion.immobilier.nc/photos/img2.jpg"},
            {"thumbnail": "https://gestion.immobilier.nc/photos/img3.jpg"},
        ]
    }
    raw = scraper.parse_item_to_raw_listing(item_multi)
    assert raw is not None
    assert raw.image_url == "https://gestion.immobilier.nc/photos/img1.jpg"
    assert raw.images_json is not None

    parsed_imgs = json.loads(raw.images_json)
    assert len(parsed_imgs) == 3
    assert parsed_imgs[0] == "https://gestion.immobilier.nc/photos/img1.jpg"
    assert parsed_imgs[1] == "https://gestion.immobilier.nc/photos/img2.jpg"
    assert parsed_imgs[2] == "https://gestion.immobilier.nc/photos/img3.jpg"

    cleaned = cleaner.clean(raw)
    assert cleaned is not None
    assert cleaned.image_url == raw.image_url
    assert cleaned.images_json == raw.images_json

    # Test stockage DuckDB
    test_db_path = tmp_path / "test_photos.duckdb"
    db = PropertyDatabase(test_db_path)
    db.upsert_listings([cleaned])

    stored = db.query("SELECT image_url, images_json FROM listings WHERE id = 'bienmeloger.nc_777888' OR id = 'immobilier.nc_777888'")
    assert len(stored) == 1
    assert stored.iloc[0]["image_url"] == "https://gestion.immobilier.nc/photos/img1.jpg"
    assert stored.iloc[0]["images_json"] == raw.images_json


def test_typology_detection(cleaner):
    # 1. Studio -> rooms = 1, bedrooms = 0
    r_studio, b_studio = cleaner.parse_rooms(None, "Location joli studio meublé centre-ville")
    assert r_studio == 1
    assert b_studio == 0

    # 2. F1 / F2 / F3 / F4
    r1, _ = cleaner.parse_rooms("F1", "Appartement F1")
    assert r1 == 1

    r2, b2 = cleaner.parse_rooms("F2", "Bel appartement F2")
    assert r2 == 2
    assert b2 == 1

    r3, b3 = cleaner.parse_rooms("F3", "Villa F3")
    assert r3 == 3
    assert b3 == 2

    r4, b4 = cleaner.parse_rooms("F4", "Maison F4 avec 3 chambres")
    assert r4 == 4
    assert b4 == 3

    # 3. >F5 / F5+
    r5, _ = cleaner.parse_rooms(">F5", "Grande villa >F5 de standing")
    assert r5 >= 5

    # 4. Protection contre les faux positifs (UUIDs / hashes / balises IMG)
    r_terrain, _ = cleaner.parse_rooms(None, "[IMG: https://storage.googleapis.com/test/fc4e4635-f750-4009.jpg] Terrain de 30 ares")
    assert r_terrain is None

    # 5. Non-residential classification
    raw_terrain = RawListing(
        source="test",
        source_id="terrain_01",
        url="https://test/terrain_01",
        title="Terrain plat de 10 ares à Dumbéa",
        description="Magnifique parcelle viabilisée.",
        raw_price="12 000 000 F",
        raw_surface="1000 m²",
        property_type_declared="terrain",
    )
    cleaned_t = cleaner.clean(raw_terrain)
    assert cleaned_t is not None
    assert cleaned_t.rooms is None
    assert cleaned_t.room_type is None
    assert cleaned_t.room_type_code is None

    # 6. Residential CleanedListing computed fields
    raw_appt = RawListing(
        source="test",
        source_id="appt_01",
        url="https://test/appt_01",
        title="Appartement F3 avec terrasse Nouméa",
        description="Résidence calme avec 2 chambres.",
        raw_price="28 000 000 F",
        raw_surface="75 m²",
        property_type_declared="appartement",
    )
    cleaned_a = cleaner.clean(raw_appt)
    assert cleaned_a is not None
    assert cleaned_a.rooms == 3
    assert cleaned_a.room_type == "F3"
    assert cleaned_a.room_type_code == "3"


def test_furnished_parsing(cleaner):
    # 1. Via facilities list (API immobilier.nc)
    assert cleaner.parse_furnished(
        facilities=["meuble", "climatisation"],
        title="Appartement F2",
        description="Joli F2 à l'Anse Vata",
        property_type=PropertyType.APPARTEMENT,
        transaction_type=TransactionType.LOCATION,
    ) is True

    # 2. Via explicit title/description "meublé"
    assert cleaner.parse_furnished(
        facilities=None,
        title="Appartement F3 meublé à Nouméa",
        description="Entièrement meublé et équipé",
        property_type=PropertyType.APPARTEMENT,
        transaction_type=TransactionType.LOCATION,
    ) is True

    # 3. Via explicit "non meublé" / "loué vide"
    assert cleaner.parse_furnished(
        facilities=None,
        title="Maison F4 à Dumbéa",
        description="Logement loué vide avec jardin",
        property_type=PropertyType.MAISON_VILLA,
        transaction_type=TransactionType.LOCATION,
    ) is False

    # 4. Negation priority over virtual staging disclaimer
    assert cleaner.parse_furnished(
        facilities=None,
        title="Appartement meublé F3",
        description="Les images meublées sont des projections IA. Le logement est actuellement loué non meublé.",
        property_type=PropertyType.APPARTEMENT,
        transaction_type=TransactionType.LOCATION,
    ) is False

    # 5. Prevention of false-positive "immeuble"
    assert cleaner.parse_furnished(
        facilities=None,
        title="Appartement F2 au centre-ville",
        description="Situé au 3ème étage de l'immeuble Le Foch.",
        property_type=PropertyType.APPARTEMENT,
        transaction_type=TransactionType.LOCATION,
    ) is None

    # 6. CleanedListing integration & computed property furnished_label
    raw_meuble = RawListing(
        source="immobilier.nc",
        source_id="m1",
        url="https://test/m1",
        title="Studio meublé Baie des Citrons",
        description="Studio entièrement meublé face mer.",
        raw_price="85 000 F/mois",
        raw_surface="28 m²",
        property_type_declared="appartement",
        transaction_type_declared="Location",
        facilities=["meuble"],
    )
    cleaned_m = cleaner.clean(raw_meuble)
    assert cleaned_m is not None
    assert cleaned_m.is_furnished is True
    assert cleaned_m.furnished_label == "Meublé"

    raw_non_meuble = RawListing(
        source="immobilier.nc",
        source_id="nm1",
        url="https://test/nm1",
        title="F2 à Magenta",
        description="Appartement loué non meublé.",
        raw_price="95 000 F/mois",
        raw_surface="45 m²",
        property_type_declared="appartement",
        transaction_type_declared="Location",
    )
    cleaned_nm = cleaner.clean(raw_non_meuble)
    assert cleaned_nm is not None
    assert cleaned_nm.is_furnished is False
    assert cleaned_nm.furnished_label == "Non meublé"


def test_published_at_and_price_history(tmp_path, cleaner):
    from datetime import datetime, timezone
    
    test_db_path = tmp_path / "test_history.duckdb"
    db = PropertyDatabase(test_db_path)
    
    pub_date = datetime(2025, 8, 1, 12, 0, tzinfo=timezone.utc)
    raw = RawListing(
        source="immobilier.nc",
        source_id="hist_1",
        url="https://test/hist1",
        title="Maison F4 Anse Vata Nouméa",
        description="Belle maison avec jardin",
        raw_price="50 000 000 F",
        raw_surface="120 m²",
        property_type_declared="maison",
        transaction_type_declared="Vente",
        published_at=pub_date,
    )
    
    cleaned = cleaner.clean(raw)
    assert cleaned is not None
    assert cleaned.published_at == pub_date
    assert cleaned.initial_price_xpf == 50_000_000
    assert cleaned.first_seen_at == pub_date
    
    # 1. Insertion initiale
    db.upsert_listings([cleaned])
    
    with db.get_connection() as con:
        row = con.execute("SELECT price_xpf, initial_price_xpf, published_at FROM listings WHERE id = 'immobilier.nc_hist_1'").fetchone()
        assert row[0] == 50_000_000
        assert row[1] == 50_000_000
        assert row[2] is not None
        
        hist = con.execute("SELECT event_type, price_xpf, price_change_xpf, price_change_pct FROM listing_price_history WHERE listing_id = 'immobilier.nc_hist_1'").fetchall()
        assert len(hist) == 1
        assert hist[0][0] == "INITIAL"
        assert hist[0][1] == 50_000_000
        
    # 2. Baisse de prix à 47 000 000 F (-6%)
    raw_dropped = RawListing(
        source="immobilier.nc",
        source_id="hist_1",
        url="https://test/hist1",
        title="Maison F4 Anse Vata Nouméa",
        description="Belle maison avec jardin",
        raw_price="47 000 000 F",
        raw_surface="120 m²",
        property_type_declared="maison",
        transaction_type_declared="Vente",
        published_at=pub_date,
    )
    cleaned_dropped = cleaner.clean(raw_dropped)
    db.upsert_listings([cleaned_dropped])
    
    with db.get_connection() as con:
        row = con.execute("SELECT price_xpf, initial_price_xpf, last_price_change_at FROM listings WHERE id = 'immobilier.nc_hist_1'").fetchone()
        assert row[0] == 47_000_000
        assert row[1] == 50_000_000  # Le prix initial est fidèlement préservé
        assert row[2] is not None
        
        hist = con.execute("SELECT event_type, price_xpf, price_change_xpf, price_change_pct FROM listing_price_history WHERE listing_id = 'immobilier.nc_hist_1' ORDER BY recorded_at ASC").fetchall()
        assert len(hist) == 2
        assert hist[1][0] == "PRICE_DROP"
        assert hist[1][1] == 47_000_000
        assert hist[1][2] == -3_000_000
        assert round(hist[1][3], 1) == -6.0


def test_dock_and_commercial_rental_classification(cleaner):
    """Vérifie que les docks industriels et locaux avec loyer mensuel sont classés en LOCATION."""
    # Cas de l'annonce réelle Dock à Numbo
    raw = RawListing(
        source="immobilier.nc",
        source_id="485214",
        url="https://www.immobilier.nc/details/485214",
        title="Dock à Nouméa (Numbo)",
        description="Dock construit en dur, avec une hauteur de 5m70, quatre bureaux et bloc sanitaire, + mezzanine de 130M² pour stockage. Avec parkings.",
        raw_price="360000 F CFP/mois",
        raw_surface="488 m²",
        property_type_declared="Dock",
        transaction_type_declared="Location",
    )
    cleaned = cleaner.clean(raw)
    assert cleaned is not None
    assert cleaned.transaction_type == TransactionType.LOCATION
    assert cleaned.price_xpf == 360_000
    assert cleaned.surface_habitable_m2 == 488.0
    assert cleaned.prix_m2_habitable_xpf == round(360_000 / 488.0, 2)


def test_sale_with_rental_investment_keywords(cleaner):
    """Vérifie que les annonces de vente mentionnant la rentabilité locative restent bien en VENTE."""
    raw = RawListing(
        source="immobilier.nc",
        source_id="512398",
        url="https://test/512398",
        title="Maison F6 à Nouméa (Baie des citrons)",
        description="À VENDRE ensemble immobilier exceptionnel. Idéal pour investissement locatif avec possibilité de mise en location saisonnière à forte rentabilité.",
        raw_price="115 000 000 F CFP",
        raw_surface="211 m²",
        property_type_declared="maison",
        transaction_type_declared="Vente",
    )
    cleaned = cleaner.clean(raw)
    assert cleaned is not None
    assert cleaned.transaction_type == TransactionType.VENTE
    assert cleaned.price_xpf == 115_000_000


def test_financial_guardrails_thresholds(cleaner):
    """Vérifie l'application stricte des seuils plancher et plafond financiers calédoniens."""
    # Prix < 1.5M sans déclaration explicite -> LOCATION obligatoire
    raw_under_1_5m = RawListing(
        source="test",
        source_id="test_under",
        url="http://test",
        title="Appartement F2 Pouembout",
        description="Joli F2 calme",
        raw_price="65 000 F CFP",
        raw_surface="40 m²",
    )
    cleaned = cleaner.clean(raw_under_1_5m)
    assert cleaned is not None
    assert cleaned.transaction_type == TransactionType.LOCATION

    # Prix > 3M sans indication de loyer mensuel -> VENTE obligatoire
    raw_over_3m = RawListing(
        source="test",
        source_id="test_over",
        url="http://test",
        title="Terrain Robinson Mont-Dore",
        description="Beau terrain plat viabilisé",
        raw_price="18 000 000 F CFP",
        raw_surface="800 m²",
    )
    cleaned = cleaner.clean(raw_over_3m)
    assert cleaned is not None
    assert cleaned.transaction_type == TransactionType.VENTE


def test_database_upsert_updates_transaction_type(tmp_path, cleaner):
    """Vérifie que l'upsert DuckDB met bien à jour transaction_type sur conflit d'ID."""
    test_db_path = tmp_path / "test_upsert_tt.duckdb"
    db = PropertyDatabase(test_db_path)

    # 1. Insertion erronée initiale en VENTE
    raw_v1 = RawListing(
        source="test",
        source_id="numbo_test",
        url="http://test/numbo",
        title="Dock Numbo",
        description="Grand dock",
        raw_price="360 000 000 F CFP",
        raw_surface="488 m²",
        transaction_type_declared="Vente",
        property_type_declared="Dock",
    )
    c1 = cleaner.clean(raw_v1)
    db.upsert_listings([c1])

    with db.get_connection() as con:
        res = con.execute("SELECT transaction_type, price_xpf FROM listings WHERE id = 'test_numbo_test'").fetchone()
        assert res[0] == "VENTE"
        assert res[1] == 360_000_000

    # 2. Mise à jour avec la bonne information en LOCATION
    raw_v2 = RawListing(
        source="test",
        source_id="numbo_test",
        url="http://test/numbo",
        title="Dock Numbo",
        description="Grand dock",
        raw_price="360 000 F CFP/mois",
        raw_surface="488 m²",
        transaction_type_declared="Location",
        property_type_declared="Dock",
    )
    c2 = cleaner.clean(raw_v2)
    db.upsert_listings([c2])

    with db.get_connection() as con:
        res = con.execute("SELECT transaction_type, price_xpf FROM listings WHERE id = 'test_numbo_test'").fetchone()
        assert res[0] == "LOCATION"
        assert res[1] == 360_000






