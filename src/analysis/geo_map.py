"""
Module de génération de la carte géospatiale interactive du Grand Nouméa (Folium / HTML).
Visualisation des indicateurs de prix au m², rendements locatifs et segmentations de quartiers.
"""

from pathlib import Path
from typing import Optional
import folium
from folium import plugins

from src.config.settings import PROCESSED_DATA_DIR, XPF_TO_EUR_RATE
from src.reference.geo import GeoReferential
from src.storage.database import PropertyDatabase
from src.valuation.constants import PRIX_BASE_M2_QUARTIER, FACTEUR_LIQUIDITE_SECTEUR, RENDEMENT_LOCATIF_BRUT_SECTEUR
from src.valuation.avm import HedonicValuationEngine


class GrandNoumeaMapGenerator:
    def __init__(self, db: Optional[PropertyDatabase] = None, geo_ref: Optional[GeoReferential] = None):
        self.db = db or PropertyDatabase()
        self.geo_ref = geo_ref or GeoReferential()
        self.engine = HedonicValuationEngine(self.geo_ref)

    def _get_color_for_price(self, prix_m2: int) -> str:
        """Détermine la couleur du marqueur en fonction de la tranche de prix au m²."""
        if prix_m2 >= 500_000:
            return "#d90429"  # Rouge vif (Premium côtier)
        elif prix_m2 >= 400_000:
            return "#f77f00"  # Orange (Haut de gamme / Résidentiel prisé)
        elif prix_m2 >= 300_000:
            return "#0077b6"  # Bleu (Intermédiaire / Périurbain standing)
        else:
            return "#2a9d8f"  # Vert canard (Accessible / Populaire)

    def generate_map(self, output_path: Optional[Path] = None) -> Path:
        """Génère la carte interactive complète et l'enregistre en fichier HTML."""
        target_file = output_path or (PROCESSED_DATA_DIR / "carte_marche_grand_noumea.html")
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Centre géographique du Grand Nouméa
        center_lat, center_lon = -22.23, 166.47
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11,
            tiles="OpenStreetMap",
            control_scale=True,
        )

        # FeatureGroups pour filtrer les calques
        fg_prix = folium.FeatureGroup(name="Valorisation au m² (Vente)", show=True)
        fg_rendement = folium.FeatureGroup(name="Rendements Locatifs Bruts", show=False)

        # Parcourir chaque commune et chaque quartier du référentiel
        communes_data = self.geo_ref.data.get("communes", {})

        for com_key, com_info in communes_data.items():
            commune_nom = com_info["nom"]
            for q in com_info.get("quartiers", []):
                q_nom = q["nom"]
                lat = q.get("latitude")
                lon = q.get("longitude")

                if not lat or not lon:
                    continue

                # Déterminer les prix et indicateurs de marché
                commune_enum = self.geo_ref.communes_map.get(commune_nom.lower())
                sector_key = self.engine._get_sector_key(commune_enum, q_nom)
                facteur_liq = FACTEUR_LIQUIDITE_SECTEUR.get(sector_key, 0.90)
                rendement_brut = RENDEMENT_LOCATIF_BRUT_SECTEUR.get(sector_key, 0.06) * 100

                # Prix de référence
                base_prices = PRIX_BASE_M2_QUARTIER.get(commune_enum, {}).get(q_nom, (350_000, 330_000))
                prix_m2_appt, prix_m2_villa = base_prices
                prix_m2_moyen = int((prix_m2_appt + prix_m2_villa) / 2)
                prix_m2_eur = int(prix_m2_moyen / XPF_TO_EUR_RATE)

                color = self._get_color_for_price(prix_m2_moyen)

                # Style du popup HTML soigné
                popup_html = f"""
                <div style="font-family: Arial, sans-serif; width: 260px; font-size: 13px; line-height: 1.4;">
                    <div style="background-color: {color}; color: white; padding: 6px 10px; border-radius: 4px 4px 0 0;">
                        <h4 style="margin: 0; font-size: 14px;">{q_nom}</h4>
                        <span style="font-size: 11px; opacity: 0.9;">{commune_nom} • {q.get('secteur', '')}</span>
                    </div>
                    <div style="padding: 10px; background-color: #fafafa; border: 1px solid #ddd; border-top: none; border-radius: 0 0 4px 4px;">
                        <p style="margin: 0 0 8px 0; color: #555; font-style: italic;">{q.get('description', '')}</p>
                        <hr style="border: none; border-top: 1px solid #eee; margin: 6px 0;" />
                        <b>Prix indicatif au m² :</b><br/>
                        • Appartement : <span style="color: #111; font-weight: bold;">{prix_m2_appt:,} F/m²</span><br/>
                        • Villa : <span style="color: #111; font-weight: bold;">{prix_m2_villa:,} F/m²</span><br/>
                        • Équivalent : <b>{prix_m2_eur:,} €/m²</b><br/>
                        <hr style="border: none; border-top: 1px solid #eee; margin: 6px 0;" />
                        <b>Rendement locatif brut :</b> <span style="color: green; font-weight: bold;">{rendement_brut:.1f} %</span><br/>
                        <b>Indice de liquidité post-2024 :</b> <b>{facteur_liq:.2f}</b><br/>
                        <b>Standing :</b> {q.get('standing', 'Standard')}
                    </div>
                </div>
                """.replace(",", " ")

                # 1. Pastille sur le calque de prix
                radius = 10 if prix_m2_moyen >= 450_000 else 7
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=radius,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"<b>{q_nom}</b> : {prix_m2_moyen:,} F/m² ({rendement_brut:.1f}%)".replace(",", " "),
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.75,
                    weight=2,
                ).add_to(fg_prix)

                # 2. Pastille sur le calque de rendement (couleur selon le rendement)
                rendement_color = "green" if rendement_brut >= 6.5 else ("orange" if rendement_brut >= 5.8 else "purple")
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=8,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"<b>{q_nom}</b> : Rendement brut {rendement_brut:.1f}%",
                    color=rendement_color,
                    fill=True,
                    fill_color=rendement_color,
                    fill_opacity=0.8,
                    weight=2,
                ).add_to(fg_rendement)

        fg_prix.add_to(m)
        fg_rendement.add_to(m)

        # Légende statique flottante
        legend_html = """
        <div style="position: fixed; 
                    bottom: 25px; right: 25px; width: 230px; height: 160px; 
                    background-color: white; z-index:9999; font-size:12px;
                    border:2px solid #bbb; border-radius: 6px; padding: 10px;
                    box-shadow: 2px 2px 6px rgba(0,0,0,0.2); font-family: Arial, sans-serif;">
            <b>Prix au m² - Grand Nouméa</b><br>
            <i style="background:#d90429; width:12px; height:12px; float:left; margin-right:8px; border-radius:50%;"></i> &gt; 500 000 F/m² (Premium)<br>
            <i style="background:#f77f00; width:12px; height:12px; float:left; margin-right:8px; border-radius:50%;"></i> 400 000 - 500 000 F/m²<br>
            <i style="background:#0077b6; width:12px; height:12px; float:left; margin-right:8px; border-radius:50%;"></i> 300 000 - 400 000 F/m²<br>
            <i style="background:#2a9d8f; width:12px; height:12px; float:left; margin-right:8px; border-radius:50%;"></i> &lt; 300 000 F/m² (Accessible)<br>
            <hr style="margin: 6px 0;">
            <small>Parité fixe : 1 EUR = 119.33 XPF</small>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        folium.LayerControl(collapsed=False).add_to(m)
        m.save(str(target_file))
        return target_file
