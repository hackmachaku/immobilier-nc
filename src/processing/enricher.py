import re
from typing import Optional
from src.models.listing import CleanedListing
from src.reference.geo import GeoReferential


class ListingEnricher:
    def __init__(self, geo_ref: Optional[GeoReferential] = None):
        self.geo_ref = geo_ref or GeoReferential()

    def enrich(self, listing: CleanedListing) -> CleanedListing:
        """
        Enrichit l'annonce avec des attributs prédictifs (vue mer, piscine, climatisation, standing).
        """
        text = f"{listing.title} {listing.description}".lower()

        # 1. Vue mer / lagon (prime de valeur majeure dans le Grand Nouméa)
        sea_view_regex = r"\b(vue\s*mer|vue\s*lagon|vue\s*baie|vue\s*imprenable\s*sur\s*la\s*mer|face\s*(?:a|à)\s*la\s*mer|front\s*de\s*mer|bord\s*de\s*mer|apercu\s*mer|acces\s*direct\s*plage)\b"
        listing.has_sea_view = bool(re.search(sea_view_regex, text))

        # 2. Piscine (très valorisée pour les villas et résidences de standing)
        pool_regex = r"\b(piscine|bassin|spa\s*pool|couloir\s*de\s*nage|jacuzzi)\b"
        listing.has_pool = bool(re.search(pool_regex, text))

        # 3. Climatisation (confort thermique essentiel en climat tropical calédonien)
        ac_regex = r"\b(climatise|climatisee|climatisations?|clim\b|clims\b)\b"
        listing.has_air_conditioning = bool(re.search(ac_regex, text))

        # 4. Sécurité (critère de plus en plus surveillé post-2024)
        security_regex = r"\b(securise|securisee|digicode|interphone|gardien|alarme|volets\s*roulants|portail\s*electrique|cloture)\b"
        listing.is_secured = bool(re.search(security_regex, text))

        # 5. Standing estimé
        prestige_regex = r"\b(prestige|haut\s*standing|luxe|renove\s*avec\s*gout|materiaux\s*nobles|kohu|deck\s*en\s*kohu|villa\s*d\s*architecte)\b"
        if re.search(prestige_regex, text):
            listing.standing_estime = "PREMIUM"
        elif listing.quartier:
            # Récupération du standing territorial moyen
            q_info = self.geo_ref.get_quartier_info(listing.commune, listing.quartier)
            if q_info:
                listing.standing_estime = q_info.get("standing", "INTERMEDIAIRE").upper()
        else:
            listing.standing_estime = "STANDARD"

        return listing
