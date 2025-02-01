import streamlit as st
import pandas as pd
import unidecode

# Chargement des données
@st.cache_data
def load_data():
    """
    Loads data from a CSV file.

    Returns:
    pandas.DataFrame: The loaded data.
    """
    data = pd.read_parquet("petitions_fr-FR_20245_predicted_FR_CS_C23.parquet")
    return data

# Pré-traitement des données
@st.cache_data
def preprocess_data(df):
    df['year'] = pd.DatetimeIndex(df['date']).year
    df = df.dropna(subset=['description'])  # Suppression des lignes où 'description' est manquant
    df = df.drop_duplicates(subset=['id'])  # Suppression des doublons basés sur 'id'

    # Concaténation des colonnes pour créer 'title_description'
    df['title_description'] = (
        df['title'].fillna('') + " " +
        df['description'].fillna('') + " " +
        df['target'].fillna('')
    )
    
    # Transformation en minuscules, suppression des caractères spéciaux et gestion des NaN
    df['title_description'] = (
        df['title_description']
        .fillna('')  # Remplacer les NaN par des chaînes vides
        .astype(str)  # Forcer la conversion en chaîne
        .str.lower()  # Convertir en minuscules
        .str.replace("[,.;:!]", " ", regex=True)  # Supprimer les caractères spéciaux
    )
    
    # Application de unidecode
    df['title_description'] = df['title_description'].apply(unidecode.unidecode)

    return df

# Fonction de filtrage
@st.cache_data
def filter_data(input_df, communes_list, min_signatures, min_year, max_year):
    # Normalisation des noms de communes
    communes = [unidecode.unidecode(word).lower() for word in communes_list]
    tmp = [word.replace("saint", "st") for word in communes if "saint" in word]
    communes.extend([unidecode.unidecode(word) for word in tmp])
    communes.extend([unidecode.unidecode(word.replace("-", " ")) for word in communes if "-" in word])

    def funct(liste, phrase):
        for word in liste:
            if f" {word.lower()} " in f" {phrase.lower()} ":
                return True
        return False

    df = input_df
    df = df[df['total_signature_count'] >= min_signatures]
    df = df[(df['year'] <= max_year) & (df['year'] >= min_year)]
    df = df[df["title_description"].apply(lambda x: funct(communes, x))]

    # Ajout des colonnes dynamiques
    df["ville"] = df["title_description"].apply(lambda x: ville(communes, x))
    df["villes"] = df["title_description"].apply(lambda x: villes(communes, x))
    df["villes_cpt"] = df["title_description"].apply(lambda x: villes_cpt(communes, x))

    return df

# Fonctions pour les colonnes supplémentaires
def ville(liste, phrase):
    for word in liste:
        if f" {word.lower()} " in f" {phrase.lower()} ":
            return word
    return None

def villes(liste, phrase):
    return [word for word in liste if f" {word.lower()} " in f" {phrase.lower()} "]

def villes_cpt(liste, phrase):
    return sum(1 for word in liste if f" {word.lower()} " in f" {phrase.lower()} ")

# Streamlit App
st.title("Filtres de pétitions")

# Chargement des données
df = preprocess_data(load_data())

# Groupes de colonnes définis
SOCIETAL_SCORES_COL = [
    "Education", "Politique", "Protection Animale", "Droit de l’enfance",
    "Environnement", "Justice Economique", "Santé", "Sport", "Justice",
    "Vie Locale", "Mobilité", "Santé - Précaution Ondes", "Droit des femmes"
]
DYNAMIC_COLUMNS = ["ville", "villes", "villes_cpt"]
custom_column_order = [
    "id", "year", "date", "title", "description", "target", "title_description",
    "processed_datea", "total_signature_count", "dominant topic", "dominant score"
] + DYNAMIC_COLUMNS + SOCIETAL_SCORES_COL
EXCLUDED_COLUMNS = ["themes", "themes_MC"]

# Option pour inclure les scores de valeurs sociétales
include_societal_scores = st.checkbox("Inclure les scores de chaque valeurs sociétales", value=False)

# Mettre à jour les colonnes disponibles dynamiquement
available_columns = [col for col in custom_column_order if col not in EXCLUDED_COLUMNS]
if not include_societal_scores:
    available_columns = [col for col in available_columns if col not in SOCIETAL_SCORES_COL]

# Si l'utilisateur change l'état de l'option, recharger la page
if "include_societal_scores_state" not in st.session_state:
    st.session_state["include_societal_scores_state"] = include_societal_scores

if st.session_state["include_societal_scores_state"] != include_societal_scores:
    st.session_state["include_societal_scores_state"] = include_societal_scores
    st.rerun()

# Formulaire principal
with st.form("parametres"):
    st.subheader("Paramètres des filtres")

    # Champs côte à côte pour l'année et les signatures
    col1, spacer, col2 = st.columns([2,0.5,2])

    with col1:
        #slider pour sélectionner une plage d'années
        year_range = st.slider(
            "Filtrer par plage d'années (années incluses) :", 
            min_value=2008, 
            max_value=2025, 
            value=(2008,2025), # Plage par défaut
            help="Sélectionner une plage d'année pour filtrer les pétitions."
        )
    
        #Extraire l'année maximale et minimale
        min_year, max_year = year_range

    with col2:
        min_signatures = st.number_input(
            "Nombre minimum de signatures :", 
            min_value=0, 
            value=0, 
            step=10, 
            help="Indiquez le nombre minimum de signatures requis."
        )

    # Autres champs du formulaire
    communes_input = st.text_area("Liste des communes / mots-clés :", "Aigaliers, Aigremont, Aigues-Mortes",
                                  help="""Indiquez les noms des communes séparés par des virgules.
                                  \nNB1: Plusieurs communes peuvent avoir le même nom.
                                  \nNB2: Des communes peuvent avoir le même nom que des noms communs et fausser la recherche (Ex: Rivières, Les Plans, Visé, Portes...)""")
    communes = [c.strip() for c in communes_input.split(",")]
    # Texte explicatif sous le champ
    st.markdown("""
                <p style="font-size: 12px; color: rgba(100, 100, 100, 0.7); font-style: italic;">
                Exemple : Aigaliers, Aigremont, Aigues-Mortes, Saint-Laurent-des-Arbres</p>
                """,
                unsafe_allow_html=True)

    # Sélection des colonnes pour le CSV
    available_columns = [col for col in custom_column_order if col not in EXCLUDED_COLUMNS]
    if not include_societal_scores:
        available_columns = [col for col in available_columns if col not in SOCIETAL_SCORES_COL]

    selected_columns = st.multiselect(
        "Colonnes à inclure dans le fichier CSV :", available_columns, default=available_columns
    )

    # Bouton pour appliquer les filtres
    submitted = st.form_submit_button("Appliquer les filtres")

# Traitement après soumission du formulaire
if submitted:
    filtered_df = filter_data(df, communes, min_signatures, min_year, max_year)
    filtered_df = filtered_df.sort_values("total_signature_count", ascending=False)
    display_columns = [col for col in custom_column_order if col in filtered_df.columns and col in selected_columns]

    st.write(f"Résultats : {len(filtered_df)} pétitions trouvées.")
    st.dataframe(filtered_df[display_columns].head(50))

    # Générer et télécharger le fichier CSV
    final_df = filtered_df[display_columns]
    csv = final_df.to_csv(index=False)
    st.download_button("Télécharger les résultats en CSV", data=csv, file_name="filtered_pétitions.csv", mime="text/csv")