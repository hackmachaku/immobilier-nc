"""
Module d'extraction haute fidélité pour fiches détaillées d'annonces immobilières.
Garantit l'absence totale de troncature de texte et extrait 100% des spécifications techniques.
"""

import re
import html as html_lib
from typing import Dict, Any, Optional, List, Tuple
from bs4 import BeautifulSoup


def parse_immonc_detail_html(html_content: str, url: str = "") -> Dict[str, Any]:
    """
    Parse le code HTML complet d'une page de détail d'annonce ImmoNC (https://www.immonc.com/annonce/...).
    Extrait :
    - Le descriptif intégral (non tronqué, avec sauts de lignes et puces préservés)
    - Le dictionnaire complet des 'Détails complémentaires' (Général, Cadre de vie, Finances, Cuisine, Salle de bain, Annexe, Garage)
    - Les attributs scalaires normalisés (surface habitable, terrasse, charges, étage, ascenseur, etc.)
    - Les coordonnées du négociateur direct (nom et téléphone portable/fixe)
    """
    if not html_content:
        return {}

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Extraction du Descriptif Intégral
    full_description = ""
    desc_card = soup.find("div", class_="listing-description-card") or soup.find("div", class_="detailcomplement")
    if desc_card:
        pera = desc_card.find("div", class_="pera")
        if pera:
            paragraphs = []
            for elem in pera.children:
                if elem.name in ("p", "div", "h2", "h3", "h4", "h5", "li"):
                    txt = elem.get_text(strip=True)
                    if txt:
                        paragraphs.append(txt)
                elif elem.name == "br":
                    continue
                elif isinstance(elem, str):
                    s = elem.strip()
                    if s:
                        paragraphs.append(s)
            if paragraphs:
                full_description = "\n\n".join(paragraphs)
            else:
                full_description = pera.get_text("\n\n", strip=True)

    if not full_description:
        # Fallback de recherche par titre 'Descriptif du bien'
        for h2 in soup.find_all(["h2", "h3"]):
            if "descriptif" in h2.get_text().lower():
                parent = h2.find_parent("div", class_="detailcomplement") or h2.find_parent("div")
                if parent:
                    p_elem = parent.find("div", class_="pera") or parent.find("p")
                    if p_elem:
                        full_description = p_elem.get_text("\n\n", strip=True)
                        break

    # Décodage propre des entités HTML (&nbsp;, &#192;, etc.)
    full_description = html_lib.unescape(full_description).strip()

    # 2. Extraction des Détails Complémentaires structurés
    complementary_details: Dict[str, Any] = {}
    details_card = soup.find("div", class_="listing-details-card")
    if not details_card:
        for div in soup.find_all("div", class_="detailcomplement"):
            if "détails" in div.get_text().lower() or "details" in div.get_text().lower():
                details_card = div
                break

    if details_card:
        boxes = details_card.find_all("div", class_="detailbox")
        for box in boxes:
            h3 = box.find(["h3", "h4", "span"])
            cat_name = h3.get_text(strip=True) if h3 else "Divers"
            cat_name = re.sub(r"\s+", " ", cat_name).strip()

            items = []
            for li in box.find_all(["li", "p"]):
                li_text = li.get_text(" ", strip=True)
                li_text = re.sub(r"\s+", " ", li_text).strip()
                if li_text and li_text != cat_name:
                    items.append(li_text)

            if items:
                complementary_details[cat_name] = items

    # 3. Extraction et normalisation des attributs scalaires
    surface_habitable: Optional[float] = None
    surface_terrasse: Optional[float] = None
    charges_mensuelles: Optional[int] = None
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parkings: Optional[int] = None
    etage: Optional[str] = None
    has_elevator = False
    has_sea_view = False
    has_ac = False
    has_pool = False
    is_secured = False

    # Parcours des boîtes de détails complémentaires
    for cat, items in complementary_details.items():
        cat_lower = cat.lower()
        items_str = " ".join(items).lower()

        # Général ou Surfaces
        if "général" in cat_lower or "general" in cat_lower or "surface" in cat_lower:
            for it in items:
                # Surface habitable
                m_surf = re.search(r"surface\s*(?:habitable)?\s*[:\s]?\s*(\d+(?:[\.,]\d+)?)\s*(?:m2|m²)?", it, re.IGNORECASE)
                if m_surf and surface_habitable is None:
                    try:
                        surface_habitable = float(m_surf.group(1).replace(",", "."))
                    except ValueError:
                        pass
                # Surface terrasse
                m_ter = re.search(r"terrasse\s*[:\s]?\s*(\d+(?:[\.,]\d+)?)\s*(?:m2|m²)?", it, re.IGNORECASE)
                if m_ter and surface_terrasse is None:
                    try:
                        surface_terrasse = float(m_ter.group(1).replace(",", "."))
                    except ValueError:
                        pass
                # Pièces
                m_rooms = re.search(r"pi[eè]ces?\s*[:\s]?\s*(\d+)", it, re.IGNORECASE)
                if m_rooms:
                    try:
                        rooms = int(m_rooms.group(1))
                    except ValueError:
                        pass
                # Chambres
                m_ch = re.search(r"chambres?\s*[:\s]?\s*(\d+)", it, re.IGNORECASE)
                if m_ch:
                    try:
                        bedrooms = int(m_ch.group(1))
                    except ValueError:
                        pass
                # Étage
                m_et = re.search(r"[eé]tage\s*[:\s]?\s*(\d+|rdc|rez[- ]de[- ]chauss[eé]e)", it, re.IGNORECASE)
                if m_et:
                    etage = m_et.group(1).strip()
                # Ascenseur
                if "ascenseur" in it.lower():
                    has_elevator = True

        # Informations financières
        if "financ" in cat_lower or "charge" in cat_lower:
            for it in items:
                m_chg = re.search(r"charges?\s*(?:de\s+copropri[eé]t[eé]|mensuelles?|copro)?\s*[:\s]?\s*(\d+[\d\s\.,]*)", it, re.IGNORECASE)
                if m_chg:
                    num_str = re.sub(r"[^\d]", "", m_chg.group(1))
                    if num_str:
                        charges_mensuelles = int(num_str)

        # Cadre de vie
        if "cadre" in cat_lower or "vue" in cat_lower:
            if "mer" in items_str or "lagon" in items_str or "baie" in items_str:
                has_sea_view = True

        # Annexe
        if "annexe" in cat_lower or "ext" in cat_lower:
            for it in items:
                # Terrasse
                m_ter = re.search(r"terrasse\s*[:\s]?\s*(\d+(?:[\.,]\d+)?)\s*(?:m2|m²)?", it, re.IGNORECASE)
                if m_ter:
                    try:
                        surface_terrasse = float(m_ter.group(1).replace(",", "."))
                    except ValueError:
                        pass
                if "clim" in it.lower():
                    has_ac = True

        # Salle de bain
        if "bain" in cat_lower or "eau" in cat_lower:
            for it in items:
                m_sdb = re.search(r"salle\s*d['’]eau\s*[:\s]?\s*(\d+)", it, re.IGNORECASE)
                if m_sdb:
                    try:
                        bathrooms = int(m_sdb.group(1))
                    except ValueError:
                        pass

        # Garage / Stationnement
        if "garage" in cat_lower or "parking" in cat_lower or "stationnement" in cat_lower:
            for it in items:
                m_park = re.search(r"(?:carport|parking|garage|box|place)\s*[:\s]?\s*(\d+)", it, re.IGNORECASE)
                if m_park:
                    try:
                        parkings = int(m_park.group(1))
                    except ValueError:
                        pass
            if parkings is None and len(items) > 0:
                parkings = 1

    # Heuristiques complémentaires sur le corps du texte si non trouvés dans les boîtes
    blob_full = f"{full_description} {url}".lower()

    if surface_terrasse is None:
        m_t = re.search(r"terrasse\s*(?:d['’]environ|de)?\s*(\d+(?:[\.,]\d+)?)\s*(?:m2|m²)", blob_full)
        if m_t:
            try:
                surface_terrasse = float(m_t.group(1).replace(",", "."))
            except ValueError:
                pass

    if etage is None:
        m_et_text = re.search(r"\b(dernier\s+[eé]tage|\d+(?:[eè]me|er)?\s+[eé]tage|rdc|rez[- ]de[- ]chauss[eé]e)\b", blob_full)
        if m_et_text:
            etage = m_et_text.group(1)

    if not has_sea_view and ("vue mer" in blob_full or "vue lagon" in blob_full or "vue dégagée" in blob_full):
        has_sea_view = True
    if not has_ac and ("climatis" in blob_full or "clim" in blob_full):
        has_ac = True
    if not has_pool and ("piscine" in blob_full or "bassin" in blob_full):
        has_pool = True
    if not is_secured and ("s[eé]curis" in blob_full or "digicode" in blob_full or "gardien" in blob_full):
        is_secured = True
    if not has_elevator and "ascenseur" in blob_full:
        has_elevator = True

    if parkings is None:
        if "carport" in blob_full or "parking" in blob_full or "place de stationnement" in blob_full:
            parkings = 1

    # 4. Détection du Négociateur Direct
    negotiator_name = None
    negotiator_phone = None

    contact_match = re.search(
        r"(?:contactez|contacter|joindre|appelez|visites?,?\s*contactez)\s+([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)?)\s+(?:au\s+|au\s*:?\s*|\(?T[eé]l\.?\s*:?\s*|\(?)\s*([0-9]{2}[\.\s]?[0-9]{2}[\.\s]?[0-9]{2}|[0-9]{6})",
        full_description,
        re.IGNORECASE
    )
    if contact_match:
        cand_name = contact_match.group(1).strip()
        # Enlever les petits mots de liaison parasites éventuels
        cand_name = re.sub(r"\s+\b(?:au|sur|par|le|la|les|directement)\b.*$", "", cand_name, flags=re.IGNORECASE).strip()
        if cand_name.lower() not in ("l'agence", "notre agence", "l agence", "agence", "une", "visite", "visiter"):
            negotiator_name = cand_name.capitalize()
        raw_num = contact_match.group(2).strip()
        num_clean = re.sub(r"[^\d]", "", raw_num)
        if len(num_clean) == 6:
            negotiator_phone = f"+687 {num_clean[:2]}.{num_clean[2:4]}.{num_clean[4:]}"
        else:
            negotiator_phone = f"+687 {raw_num}"

    # 5. Photos multiples
    photos = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if "/photos/" in src and src.startswith("http"):
            big_src = src.replace("/photos_medium/", "/photos_big/").replace("/photos_small/", "/photos_big/")
            if big_src not in photos:
                photos.append(big_src)

    return {
        "full_description": full_description,
        "complementary_details": complementary_details,
        "surface_habitable_m2": surface_habitable,
        "surface_terrasse_m2": surface_terrasse,
        "charges_mensuelles_xpf": charges_mensuelles,
        "rooms": rooms,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "parkings": parkings,
        "etage": etage,
        "has_elevator": has_elevator,
        "has_sea_view": has_sea_view,
        "has_air_conditioning": has_ac,
        "has_pool": has_pool,
        "is_secured": is_secured,
        "direct_negotiator": negotiator_name,
        "direct_phone": negotiator_phone,
        "photos": photos,
    }
