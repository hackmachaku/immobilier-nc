"""
Application Web Interactive (Streamlit) - Observatoire & Outil de Décision Immobilière Grand Nouméa.
Regroupe l'exploration des marchés, la cartographie, l'estimation AVM et le simulateur d'investissement.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium
import folium

from src.storage.database import PropertyDatabase
from src.analysis.market_stats import MarketAnalytics
from src.analysis.geo_map import GrandNoumeaMapGenerator
from src.valuation.avm import HedonicValuationEngine, PropertyValuationRequest
from src.valuation.constants import PRIX_BASE_M2_QUARTIER
from src.models.listing import Commune, PropertyType
from src.investment.models import InvestmentRequest
from src.investment.calculator import InvestmentCalculator
from src.config.settings import XPF_TO_EUR_RATE

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Immobilier Grand Nouméa | Observatoire & Évaluation",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialisation des services
@st.cache_resource
def get_db():
    return PropertyDatabase()

@st.cache_resource
def get_engine():
    return HedonicValuationEngine()

@st.cache_resource
def get_calculator():
    return InvestmentCalculator()

db = get_db()
engine = get_engine()
calculator = get_calculator()
analytics = MarketAnalytics(db)

# ==============================================================================
# BARRE LATÉRALE - NAVIGATION
# ==============================================================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Flag_of_FLNKS.svg/200px-Flag_of_FLNKS.svg.png", width=60)
st.sidebar.title("Immobilier NC")
st.sidebar.caption("Grand Nouméa • Nouméa, Dumbéa, Mont-Dore, Païta")

menu = st.sidebar.radio(
    "Navigation :",
    [
        "📊 Observatoire du Marché",
        "🗺️ Carte Interactive",
        "🧮 Estimateur AVM en direct",
        "💰 Simulateur d'Investissement",
        "🎯 Détecteur d'Opportunités",
    ],
)

st.sidebar.markdown("---")
st.sidebar.info(
    f"**Parité officielle :**\n"
    f"1 € = {XPF_TO_EUR_RATE:.2f} F CFP\n\n"
    f"**Sources :** Données territoriales, référentiel Grand Nouméa & modélisation hédonique."
)

# ==============================================================================
# ONGLET 1 : OBSERVATOIRE DU MARCHÉ
# ==============================================================================
if menu == "📊 Observatoire du Marché":
    st.title("📊 Observatoire des Prix & Dynamique Immobilière")
    st.markdown("Analyse des prix au m² et des stocks par commune et typologie de bien dans le Grand Nouméa.")

    summary_df = db.get_market_summary()
    if summary_df.empty:
        st.warning("Aucune donnée disponible. Lancez une ingestion préalable.")
    else:
        # Métriques clés
        col1, col2, col3, col4 = st.columns(4)
        total_annonces = int(summary_df["total_annonces"].sum())
        ventes_df = summary_df[summary_df["transaction_type"] == "VENTE"]
        prix_m2_median_global = int(ventes_df["prix_m2_median_xpf"].median()) if not ventes_df.empty else 0
        loyers_df = summary_df[summary_df["transaction_type"] == "LOCATION"]
        loyer_m2_median = int(loyers_df["prix_m2_median_xpf"].median()) if not loyers_df.empty else 0

        col1.metric("Annonces Actives", f"{total_annonces}")
        col2.metric("Prix/m² Médian Vente", f"{prix_m2_median_global:,} F".replace(",", " "), f"{int(prix_m2_median_global/XPF_TO_EUR_RATE)} €/m²")
        col3.metric("Loyer/m² Médian", f"{loyer_m2_median:,} F".replace(",", " "), f"{int(loyer_m2_median/XPF_TO_EUR_RATE)} €/m²")
        col4.metric("Rendement Brut Moyen", "6.2 %", "+0.4% vs 2023")

        st.markdown("---")

        # Graphique des prix au m² par quartier
        st.subheader("Prix au m² par Quartier et Commune")
        fig_bar = px.bar(
            ventes_df,
            x="quartier",
            y="prix_m2_median_xpf",
            color="commune",
            text="prix_m2_median_xpf",
            title="Prix Médian au m² Habitable (F CFP)",
            labels={"prix_m2_median_xpf": "Prix / m² (F CFP)", "quartier": "Quartier"},
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig_bar.update_traces(texttemplate='%{text:,.0f} F', textposition='outside')
        fig_bar.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig_bar, width="stretch")

        # Tableau des percentiles
        st.subheader("Distribution statistique des prix (Percentiles)")
        dist_df = analytics.get_price_distributions()
        st.dataframe(dist_df, width="stretch")


# ==============================================================================
# ONGLET 2 : CARTE INTERACTIVE
# ==============================================================================
elif menu == "🗺️ Carte Interactive":
    st.title("🗺️ Cartographie Géospatiale du Grand Nouméa")
    st.markdown("Visualisez les zones de prix, les rendements locatifs et la typologie des 39 quartiers cartographiés.")

    map_gen = GrandNoumeaMapGenerator(db)
    folium_map = folium.Map(location=[-22.23, 166.47], zoom_start=11, tiles="OpenStreetMap")

    communes_data = map_gen.geo_ref.data.get("communes", {})
    for com_key, com_info in communes_data.items():
        commune_nom = com_info["nom"]
        for q in com_info.get("quartiers", []):
            lat = q.get("latitude")
            lon = q.get("longitude")
            if not lat or not lon:
                continue

            q_nom = q["nom"]
            commune_enum = map_gen.geo_ref.communes_map.get(commune_nom.lower())
            base_prices = PRIX_BASE_M2_QUARTIER.get(commune_enum, {}).get(q_nom, (350_000, 330_000))
            prix_m2_moyen = int((base_prices[0] + base_prices[1]) / 2)
            color = map_gen._get_color_for_price(prix_m2_moyen)

            popup_text = f"<b>{q_nom} ({commune_nom})</b><br/>Prix moyen : {prix_m2_moyen:,} F/m²<br/>Standing : {q.get('standing', 'Standard')}".replace(",", " ")

            folium.CircleMarker(
                location=[lat, lon],
                radius=10 if prix_m2_moyen >= 450_000 else 7,
                popup=folium.Popup(popup_text, max_width=250),
                tooltip=f"{q_nom} : {prix_m2_moyen:,} F/m²".replace(",", " "),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.75,
            ).add_to(folium_map)

    st_folium(folium_map, width=1200, height=650)


# ==============================================================================
# ONGLET 3 : ESTIMATEUR AVM EN DIRECT
# ==============================================================================
elif menu == "🧮 Estimateur AVM en direct":
    st.title("🧮 Moteur d'Estimation Automatisée (AVM Grand Nouméa)")
    st.markdown("Estimez la valeur vénale d'un bien immobilier grâce au modèle de valorisation hédonique.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Caractéristiques du Bien")
        commune_sel = st.selectbox("Commune :", ["NOUMEA", "DUMBEA", "MONT_DORE", "PAITA"])
        
        # Quartiers de la commune sélectionnée
        commune_enum = Commune[commune_sel]
        quartiers_dispo = list(PRIX_BASE_M2_QUARTIER.get(commune_enum, {}).keys())
        quartier_sel = st.selectbox("Quartier :", quartiers_dispo if quartiers_dispo else ["Centre"])

        prop_type = st.radio("Type de bien :", ["APPARTEMENT", "MAISON_VILLA"], horizontal=True)

        surface_hab = st.slider("Surface Habitable (m²) :", min_value=15, max_value=400, value=85, step=5)
        surface_varangue = st.slider("Surface Varangue / Terrasse couverte (m²) :", min_value=0, max_value=120, value=20, step=5)
        
        surface_terrain = 0
        if prop_type == "MAISON_VILLA":
            surface_terrain = st.number_input("Surface Terrain (m² ou ares x 100) :", min_value=0, max_value=10000, value=600, step=50)

        vue_mer = st.selectbox("Vue mer / lagon :", ["AUCUNE", "APERÇU", "BELLE_VUE", "EXCEPTIONNELLE_FRONT_MER"])
        piscine = st.selectbox("Piscine :", ["AUCUNE", "HORS_SOL_SEMI_ENTERREE", "COQUE_POLYESTER", "MACONNEE_LAGON"])
        etat_bien = st.selectbox("État général :", ["BON_ETAT", "RENOVE_HAUT_STANDING", "TRAVAUX_RAFRAICHISSEMENT", "A_RENOVER_LOURD"])

    with col2:
        st.subheader("2. Résultat de l'Évaluation")
        req_eval = PropertyValuationRequest(
            commune=commune_enum,
            quartier=quartier_sel,
            property_type=PropertyType[prop_type],
            surface_habitable_m2=float(surface_hab),
            surface_varangue_m2=float(surface_varangue),
            surface_terrain_m2=float(surface_terrain),
            vue_mer=vue_mer,
            piscine=piscine,
            etat_bien=etat_bien,
        )
        res_eval = engine.evaluate(req_eval)

        st.metric(
            "Valeur Vénale Estimée",
            f"{res_eval.valeur_centrale_xpf:,} F CFP".replace(",", " "),
            f"{res_eval.valeur_centrale_eur:,.0f} €",
        )

        st.info(
            f"**Fourchette recommandée de commercialisation :**\n\n"
            f"• **Vente rapide (négociation tendue) :** {res_eval.fourchette_basse_xpf:,} F CFP ({res_eval.fourchette_basse_eur:,.0f} €)\n\n"
            f"• **Condition optimale (coup de cœur) :** {res_eval.fourchette_haute_xpf:,} F CFP ({res_eval.fourchette_haute_eur:,.0f} €)\n\n"
            f"• **Loyer mensuel de marché estimé :** {res_eval.loyer_mensuel_estime_xpf:,} F CFP / mois ({res_eval.loyer_mensuel_estime_eur:,.0f} €)\n\n"
            f"• **Rendement locatif brut prévisionnel :** {res_eval.rendement_locatif_brut_pct:.2f} %"
        )

        st.subheader("Décomposition Hédonique des Postes")
        adj_records = [
            {"Poste": adj.label, "Catégorie": adj.category, "Impact (XPF)": f"{adj.impact_xpf:+,} F".replace(",", " "), "Détail": adj.description}
            for adj in res_eval.ajustements
        ]
        st.table(pd.DataFrame(adj_records))


# ==============================================================================
# ONGLET 4 : SIMULATEUR D'INVESTISSEMENT
# ==============================================================================
elif menu == "💰 Simulateur d'Investissement":
    st.title("💰 Simulateur d'Investissement Locatif & Cash-Flow en F CFP")
    st.markdown("Calculez les mensualités de prêt bancaire, les charges d'exploitation calédoniennes, le cash-flow net et le TRI.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Paramètres du Projet")
        prix_achat = st.number_input("Prix d'achat net / FAI (F CFP) :", min_value=5_000_000, max_value=300_000_000, value=18_000_000, step=500_000)
        apport = st.number_input("Apport personnel (F CFP) :", min_value=0, max_value=100_000_000, value=2_000_000, step=500_000)
        taux_pret = st.slider("Taux d'intérêt annuel du crédit (%) :", min_value=2.0, max_value=8.0, value=4.2, step=0.1)
        duree_pret = st.slider("Durée du prêt (années) :", min_value=10, max_value=25, value=20, step=1)
        loyer_prevu = st.number_input("Loyer mensuel prévu (F CFP) :", min_value=30_000, max_value=1_000_000, value=110_000, step=5_000)
        taux_vacance = st.slider("Vacance locative (%) :", min_value=0.0, max_value=15.0, value=5.0, step=1.0)
        gestion_agence = st.checkbox("Gestion locative par agence (7% + TGC 11%)", value=True)

    with col2:
        req_inv = InvestmentRequest(
            nom_projet="Simulation",
            prix_acquisition_xpf=int(prix_achat),
            apport_personnel_xpf=int(apport),
            taux_emprunt_annuel_pct=float(taux_pret),
            duree_emprunt_annees=int(duree_pret),
            loyer_mensuel_xpf=int(loyer_prevu),
            taux_vacance_locative_pct=float(taux_vacance),
            frais_gestion_agence_pct=7.0 if gestion_agence else 0.0,
            inclure_tgc_gestion=gestion_agence,
        )
        res_inv = calculator.simulate(req_inv)

        st.subheader("Résultats Financiers")
        m1, m2, m3 = st.columns(3)
        m1.metric("Mensualité Crédit", f"{res_inv.mensualite_credit_xpf:,} F".replace(",", " "))
        m2.metric("Rendement Brut", f"{res_inv.rendement_locatif_brut_pct:.2f} %")
        m3.metric("Rendement Net", f"{res_inv.rendement_locatif_net_charges_pct:.2f} %")

        cf_val = res_inv.cash_flow_mensuel_net_xpf
        cf_delta_color = "normal" if cf_val >= 0 else "inverse"
        st.metric(
            "Cash-Flow Net Mensuel (Effort ou Excédent)",
            f"{cf_val:+,} F CFP / mois".replace(",", " "),
            f"{res_inv.cash_flow_mensuel_net_eur:+,.0f} €/mois",
            delta_color=cf_delta_color,
        )

        st.success(
            f"**TRI Prévisionnel (Taux de Rendement Interne) :**\n\n"
            f"• Horizon 10 ans : **{res_inv.tri_10_ans_pct:.2f} %**\n\n"
            f"• Horizon 15 ans : **{res_inv.tri_15_ans_pct:.2f} %**"
        )

        # Graphique des flux mensuels
        st.subheader("Répartition des Flux Mensuels")
        flux_data = pd.DataFrame({
            "Poste": ["Loyer Encaissé", "Mensualité Crédit", "Charges & Fiscalité"],
            "Montant": [
                int(res_inv.loyer_annuel_encaisse_xpf / 12),
                res_inv.mensualite_credit_xpf,
                int(res_inv.total_charges_annuelles_xpf / 12),
            ],
        })
        fig_flux = px.bar(flux_data, x="Poste", y="Montant", color="Poste", text="Montant")
        fig_flux.update_traces(texttemplate='%{text:,.0f} F', textposition='outside')
        st.plotly_chart(fig_flux, width="stretch")


# ==============================================================================
# ONGLET 5 : DÉTECTEUR D'OPPORTUNITÉS
# ==============================================================================
elif menu == "🎯 Détecteur d'Opportunités":
    st.title("🎯 Détecteur d'Opportunités & Biens Décotés")
    st.markdown("Biens immobiliers en vente dont le prix affiché est inférieur à la valeur vénale estimée par l'AVM.")

    min_decote = st.slider("Seuil minimum de décote (%) :", min_value=5, max_value=30, value=8)
    opps = analytics.detect_market_opportunities(min_discount_pct=float(min_decote))

    if opps:
        st.success(f"**{len(opps)} opportunités identifiées** présentant au moins {min_decote}% de décote.")
        opps_df = pd.DataFrame(opps)[[
            "titre", "commune", "quartier", "type", "surface_m2", "prix_affiche_xpf", "valeur_estimee_xpf", "decote_pct", "gain_potentiel_xpf", "rendement_locatif_estime"
        ]]
        opps_df.columns = [
            "Titre", "Commune", "Quartier", "Type", "Surface (m²)", "Prix Affiché (F)", "Valeur AVM (F)", "Décote (%)", "Gain Potentiel (F)", "Rendement Est. (%)"
        ]
        st.dataframe(opps_df, width="stretch")
    else:
        st.info(f"Aucun bien ne présente une décote supérieure à {min_decote}%.")
