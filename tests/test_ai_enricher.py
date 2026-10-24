"""
Tests unitaires pour le moteur d'intelligence sémantique Tier-2 Sentinel (src/processing/ai_enricher.py).
Vérifie la gestion des statuts, le paramétrage des prompts/presets, le circuit-breaker Tier-1,
le dialogue interactif et la persistance DuckDB.
"""

import pytest
from src.processing.ai_enricher import (
    check_ai_status,
    get_ai_config,
    save_ai_config,
    enrich_listing_with_ai,
    ask_ai_chat,
    get_ai_cache_stats,
    clear_ai_cache
)


def test_ai_status_and_hardware_profile():
    """Vérifie que la sonde matérielle et l'état de connectivité sont correctement reportés."""
    status = check_ai_status()
    assert "status" in status
    assert status["status"] in ("online", "offline")
    assert "hardware" in status
    hw = status["hardware"]
    assert "GTX 1060" in hw["gpu"]
    assert hw["vram_total_gb"] == 6.0
    assert hw["vram_usable_gb"] == 4.9
    assert "i7-8750H" in hw["cpu"]


def test_ai_config_and_presets():
    """Vérifie le chargement et la sauvegarde de la configuration IA avec ses presets."""
    cfg = get_ai_config()
    assert "model" in cfg
    assert "presets" in cfg
    assert "standard" in cfg["presets"]
    assert "commercial" in cfg["presets"]
    assert "contacts_only" in cfg["presets"]

    # Modification temporaire et sauvegarde
    saved = save_ai_config({"temperature": 0.15})
    assert saved["temperature"] == 0.15

    # Rétablissement
    save_ai_config({"temperature": 0.1})


def test_enrich_listing_with_ai_tier1_fallback():
    """
    Vérifie que même si Ollama est hors ligne, le circuit breaker
    active le repli déterministe Tier-1 et produit un résultat conforme au schéma JSON.
    """
    test_text = (
        "A VENDRE - LOCAL COMMERCIAL / BUREAUX 6ème KM (Rue Iekawé)\n"
        "Grande pièce principale de 30 m², 3 bureaux.\n"
        "Dock / réserve de 45 m² (hauteur 3 m).\n"
        "5 places de parking dont 2 couvertes.\n"
        "WC séparé, volets roulants électriques, climatisation intégrale.\n"
        "PRIX DE VENTE : 26 MF\n"
        "Contact : Manu – 98.72.66\n"
    )

    result = enrich_listing_with_ai(
        listing_data=test_text,
        force_refresh=True
    )

    assert "direct_contacts" in result
    assert "sections" in result
    assert "provider_used" in result

    # Vérification extraction de Manu
    contacts = result["direct_contacts"]
    assert len(contacts) >= 1
    assert any(c["name"] == "Manu" and "98.72.66" in c["phone"] for c in contacts)

    # Vérification que la taxonomie commerciale est bien appliquée (pas d'Espace Nuit)
    sections = result["sections"]
    section_titles = [s["title"] for s in sections]
    assert any("Bureaux" in t for t in section_titles)
    assert not any("Espace Nuit" in t for t in section_titles)
    assert any("Stationnement" in t for t in section_titles)


def test_ask_ai_chat_deterministic():
    """Vérifie le fonctionnement du mode dialogue sur annonce en repli déterministe."""
    listing = {
        "title": "Bureau 6ème KM",
        "currentPrice": 26000000,
        "commune": "Nouméa",
        "description": "Bureau 85 m² avec dock 45 m² et 5 parkings. Manu au 98.72.66.",
        "directContacts": [{"name": "Manu", "phone": "+687 98.72.66"}]
    }

    # Question contact
    resp_contact = ask_ai_chat(listing, "Qui dois-je contacter pour ce bureau ?")
    assert "Manu" in resp_contact["answer"]
    assert "98.72.66" in resp_contact["answer"]

    # Question parking
    resp_parking = ask_ai_chat(listing, "Y a-t-il des parkings disponibles ?")
    assert "parking" in resp_parking["answer"].lower() or "stationnement" in resp_parking["answer"].lower()


def test_ai_cache_operations():
    """Vérifie les opérations sur le cache DuckDB."""
    stats = get_ai_cache_stats()
    assert "cached_count" in stats
    cleared = clear_ai_cache()
    assert cleared is True


def test_sanitize_ai_contacts_grounding_rejects_hallucinations():
    """
    Vérifie que le Grounding Check Python rejette formellement toute fuite de prompt
    (ex: Manu 98.72.66) et résout 'contactez l'agence au 284.282' vers l'agence.
    """
    from src.processing.ai_enricher import _sanitize_ai_contacts

    raw_text = (
        "immeuble roger berard au 4ème étage, plateau de bureaux aménagés "
        "bénéficiant de 8 places de stationnement. pour les visites, contactez l'agence au 284.282 ..."
    )

    # Cas 1 : L'IA a halluciné Manu et 98.72.66 à cause d'une fuite d'exemple
    fake_contacts = [
        {"name": "Manu", "phone": "+687 98.72.66", "whatsapp": "687987266", "role": "Négociateur"}
    ]
    sanitized = _sanitize_ai_contacts(
        fake_contacts,
        raw_description=raw_text,
        agency_name="CalÃ©donienne d",
        agency_phone="+687 28.42.82"
    )

    # Manu doit impérativement être éliminé !
    assert not any(c.get("name") == "Manu" for c in sanitized)
    assert not any("98.72.66" in str(c.get("phone")) for c in sanitized)

    # Le contact doit être attribué à l'agence Calédonienne d'Immobilier au 284.282
    assert len(sanitized) >= 1
    agency_contact = sanitized[0]
    assert agency_contact["name"] == "Calédonienne d'Immobilier"
    assert "284.282" in agency_contact["phone"] or "28.42.82" in agency_contact["phone"]
    assert agency_contact["role"] == "Agence"


def test_sanitize_ai_sections_grounding_rejects_fake_bullets():
    """Vérifie que les puces de sections inventées sans fondement textuel sont éliminées."""
    from src.processing.ai_enricher import _sanitize_ai_sections

    raw_text = "immeuble roger berard au 4ème étage, plateau de bureaux aménagés bénéficiant de 8 places de stationnement."
    fake_sections = [
        {
            "key": "bureaux",
            "title": "Bureaux & Espaces professionnels",
            "items": ["Plateau de bureaux aménagés au 4ème étage", "Dock réserve de 45 m²"]
        },
        {
            "key": "stationnement",
            "title": "Stationnement & Logistique",
            "items": ["5 places de parking dont 2 couvertes", "8 places de stationnement"]
        }
    ]

    clean = _sanitize_ai_sections(fake_sections, raw_description=raw_text, title="Bureau Roger Bérard")
    all_bullets = [it for s in clean for it in s.get("items", [])]

    # Vrais éléments du texte conservés
    assert any("plateau de bureaux" in b.lower() for b in all_bullets)
    assert any("8 places" in b.lower() for b in all_bullets)

    # Hallucinations (dock 45m², 5 places) éliminées
    assert not any("dock" in b.lower() for b in all_bullets)
    assert not any("45 m²" in b.lower() for b in all_bullets)
    assert not any("5 places" in b.lower() for b in all_bullets)


def test_mojibake_and_agency_normalization():
    """Vérifie la réparation du mojibake et la résolution d'agence tronquée."""
    from src.utils.text_cleaner import fix_mojibake, normalize_agency_name

    assert normalize_agency_name("CalÃ©donienne d") == "Calédonienne d'Immobilier"
    assert normalize_agency_name("caledonienne d") == "Calédonienne d'Immobilier"
    assert fix_mojibake("bureau aménagé au 4ème étage") == "bureau aménagé au 4ème étage"
    assert "Â" not in fix_mojibake("immeuble roger berardÂ  au 4ème étage")


def test_sanitize_ai_technical_specs_grounding():
    """Vérifie l'ancrage et la détection haute fidélité des spécifications techniques."""
    from src.processing.ai_enricher import _sanitize_ai_technical_specs

    desc = (
        "Appartement F2 au dernier étage d'une résidence sécurisée avec ascenseur. "
        "Large terrasse couverte de 14 m². Place de parking couverte sécurisée. "
        "Charges de copropriété : 12 000 F/mois. Bon standing."
    )

    # 1. Spécifications conformes retournées par l'IA
    raw_specs = {
        "charges_mensuelles_xpf": 12000,
        "etage": "Dernier étage",
        "has_elevator": True,
        "parking_detail": "Place de parking couverte",
        "surface_terrasse_m2": 14.0,
        "standing": "Bon standing"
    }
    clean = _sanitize_ai_technical_specs(raw_specs, raw_description=desc)
    assert clean["charges_mensuelles_xpf"] == 12000
    assert clean["etage"] == "Dernier étage"
    assert clean["has_elevator"] is True
    assert clean["surface_terrasse_m2"] == 14.0
    assert "couverte" in clean["parking_detail"].lower()
    assert clean["standing"] == "Bon standing"

    # 2. Spécifications hallucinées par l'IA (50 000 F de charges inexistantes)
    fake_specs = {
        "charges_mensuelles_xpf": 50000,
        "surface_terrasse_m2": 85.0
    }
    clean_fake = _sanitize_ai_technical_specs(fake_specs, raw_description=desc)
    # 50 000 doit être rejeté et remplacé par les 12 000 réels trouvés dans la description
    assert clean_fake["charges_mensuelles_xpf"] == 12000
    # 85 m² doit être rejeté et remplacé par 14.0 m² réel
    assert clean_fake["surface_terrasse_m2"] == 14.0


def test_kone_f4_canonical_formatting_and_zero_loss():
    """
    Valide sur le cas réel 'Maison F4 à Extérieur (Koné)' que :
    1. Une sortie LLM dégradée ('BIEN RÉSIDENTIEL', 'kitchen équipée', '16 ares', '15m²' coupés)
       est intégralement reformatée dans le gabarit canonique invariant.
    2. Les anglicismes ('kitchen') et puces numériques orphelines ('15m²', '16 ares') disparaissent.
    3. Aucune information n'est perdue ('dont 1 privative', 'Au calme', 'Idéale pour la famille').
    4. Le contact direct 'Céline : 73.06.00' est extrait.
    """
    from src.processing.ai_enricher import _sanitize_ai_sections
    from src.processing.description_structurer import structure_description

    raw_kone = (
        "!! A VENDRE !!\n\n"
        "Seulement 18 000 000F\n\n"
        "Maison F4 INDIVIDUELLE sur un très beau terrain d'environ 16 ares avec 3 chambres climatisées, "
        "cuisine équipée, 2 salles de bain dont 1 privative, une terrasse couverte de 15m², un garage fermé.\n\n"
        "Au calme. Idéale pour la famille et 1er achat!\n\n"
        "Contactez-nous pour une visite :\n\n"
        "Céline : 73.06.00"
    )

    # Simulation de la sortie dégradée observée sur qwen2.5:1.5b avant refonte
    degraded_ai_output = [
        {
            "key": "bien_residentiel",
            "title": "BIEN RÉSIDENTIEL",
            "icon": "🏢",
            "items": [
                "Maison F4 INDIVIDUELLE",
                "16 ares",
                "3 chambres climatisées",
                "kitchen équipée",
                "2 salles de bain",
                "1 terrasse couverte",
                "15m²",
                "garage fermé"
            ]
        }
    ]

    sections = _sanitize_ai_sections(degraded_ai_output, raw_description=raw_kone, title="Maison F4 à Extérieur (Koné)", property_type="MAISON")
    sec_by_key = {s["key"]: s for s in sections}

    # 1. Aucun titre 'BIEN RÉSIDENTIEL' ne doit subsister
    assert not any("BIEN RÉSIDENTIEL" in s["title"].upper() for s in sections)

    # 2. Les rubriques canoniques attendues sont toutes présentes dans l'ordre exact
    expected_order = ["cadre_vie", "pieces_de_vie", "espace_nuit", "exterieurs", "stationnement_annexes", "conditions_modalites"]
    actual_keys = [s["key"] for s in sections if s["key"] in expected_order]
    assert actual_keys == expected_order

    # 3. Aucun anglicisme ('kitchen') ni fragment orphelin ('15m²' seul)
    all_items = [it for s in sections for it in s["items"]]
    assert not any("kitchen" in it.lower() for it in all_items)
    assert not any(it.strip() in ("15m²", "15 m²", "16 ares") for it in all_items)

    # 4. Vérification du contenu de chaque rubrique
    assert any("cuisine équipée" in it.lower() for it in sec_by_key["pieces_de_vie"]["items"])
    assert any("3 chambres climatisées" in it.lower() for it in sec_by_key["espace_nuit"]["items"])
    assert any("dont 1 privative" in it.lower() for it in sec_by_key["espace_nuit"]["items"])
    assert any("16 ares" in it.lower() for it in sec_by_key["exterieurs"]["items"])
    assert any("15 m²" in it.lower() for it in sec_by_key["exterieurs"]["items"])
    assert any("garage fermé" in it.lower() for it in sec_by_key["stationnement_annexes"]["items"])
    assert any("calme" in it.lower() or "famille" in it.lower() for it in sec_by_key["cadre_vie"]["items"])

    # 5. Contact direct Céline extrait
    t1 = structure_description(raw_kone)
    assert any(c["name"] == "Céline" and "73.06.00" in c["phone"] for c in t1["direct_contacts"])


def test_bureau_pk6_canonical_reconciliation_no_terrain():
    """
    Valide sur le cas réel 'Bureau P.k. 6' que si le LLM crée à tort une rubrique 'Terrain: 6ème KM'
    et oublie 'Surface principale : 85 m²' et '3 bureaux', la réconciliation hybride :
    - supprime le faux 'Terrain: 6ème KM',
    - restaure toutes les surfaces et les 3 bureaux dans 'Bureaux & Espaces professionnels'.
    """
    from src.processing.ai_enricher import _sanitize_ai_sections

    raw_pk6 = (
        "A VENDRE – LOCAL COMMERCIAL / BUREAUX 6ème KM (Rue Iekawé)\n"
        "Local commercial aménagé, bénéficiant d'une excellente visibilité en rez-de-chaussée d'une résidence récente au 6ème km.\n"
        "Idéal pour une activité tertiaire, médicale, restauration légère ou services.\n"
        "Surface principale : 85 m²\n"
        "Grande pièce principale de 30 m²\n"
        "3 bureaux\n"
        "Dock / réserve de 45 m² (hauteur 3 m)\n"
        "5 places de parking dont 2 couvertes\n"
        "WC séparé\n"
        "Volets roulants électriques\n"
        "Climatisation intégrale\n"
        "Contact : Manu – 98.72.66"
    )

    degraded_pk6_ai = [
        {"key": "terrain", "title": "Terrain", "items": ["6ème KM"]},
        {"key": "bureaux", "title": "Bureaux & Espaces professionnels", "items": ["WC séparé", "Volets roulants électriques", "Climatisation intégrale"]},
        {"key": "stationnement", "title": "Stationnement & Logistique", "items": ["Dock / réserve de 45 m² (hauteur 3 m)", "5 places de parking dont 2 couvertes"]}
    ]

    sections = _sanitize_ai_sections(degraded_pk6_ai, raw_description=raw_pk6, title="Bureau PK6", property_type="COMMERCIAL")
    titles = [s["title"] for s in sections]

    assert "Terrain" not in titles
    sec_bureaux = next(s for s in sections if s["key"] == "espace_nuit")
    assert sec_bureaux["title"] == "Bureaux & Espaces professionnels"
    bureaux_str = " ".join(sec_bureaux["items"]).lower()
    assert "85 m²" in bureaux_str
    assert "30 m²" in bureaux_str
    assert "3 bureaux" in bureaux_str

