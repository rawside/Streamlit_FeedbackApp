import streamlit as st
from pymongo import MongoClient
import os

# Setze das Seitenlayout auf 'wide'
st.set_page_config(layout="wide")

# MongoDB-Zugangsdaten und Verbindungszeichenfolge
mongo_conn_str = os.getenv("MONGO_CONN_STR")

# Verbindung zu MongoDB herstellen
client = MongoClient(mongo_conn_str)
db = client["BA"]
collection = db["base_cases"]
feedback_collection = db["feedback_cases"]

attribute_names = {
    "generalData.isComplete": "Ist der Fall vollständig?",
    "generalData.caseDateTime": "Schadendatum und Uhrzeit",
    "generalData.locationOfLoss": "Schadenort",
    "generalData.circumstances": "Schadenhergang",
    "involvedParties.isComplete": "Ist Beteiligter vollständig?",
    "involvedParties.partyName": "Name des Beteiligten",
    "involvedParties.damagedObject": "Beschädigtes Objekt",
    "involvedParties.partyBehavior": "Verhalten der Partei",
    "involvedParties.possibleLawArticle_svg": "mögliche SVG-Artikel",
    "involvedParties.possibleLawArticle_vrv": "Mögliche VRV-Artikel",
    "involvedParties.relevantLawArticle_svg": "Relevante SVG-Artikel",
    "involvedParties.relevantLawArticle_vrv": "Relante VRV-Artikel",
    "involvedParties.federalCourtDecisionsNeeded": "Braucht es Bundesgerichtsentscheide?",
    "involvedParties.possibleFederalCourtDecisions": "mögliche Bundesgerichtsentscheide",
    "involvedParties.relevantFederalCourtDecisions": "relevante Bundesgerichtsentscheide",
    "involvedParties.isLiable": "Ist (mit)verantwortlich",
    "involvedParties.severityOfTheFault": "Schwere des Verschuldens",
    "involvedParties.liabilityRatio": "Haftungsquote",
    "liabilityDecision.slkRelevant": "SLK-Empfehlung relevant?",
    "liabilityDecision.relevantLiabilityNorm": "Haftungsgrundlage",
    "liabilityDecision.liabilityReason": "Begründung der Haftung",
    "liabilityDecision.additionalComments": "zusätzliche Kommentare"
}

# Function to load data by caseId
def load_data(case_id):
    return collection.find_one({"caseId": case_id})


# Check if feedback exists for the given caseId
def check_feedback_exists(case_id):
    return feedback_collection.count_documents({"caseId": case_id}) > 0

# Retrieve sorted list of caseIds
case_ids = sorted([doc['caseId'] for doc in collection.find({}, {'caseId': 1})])

# Initialize or update session state
if 'current_case_id' not in st.session_state:
    st.session_state.current_case_id = case_ids[0] if case_ids else None

# Load data for the current caseId
data = load_data(st.session_state.current_case_id)

# Function to navigate to the previous or next case
def navigate_case(case_id):
    st.session_state.current_case_id = case_id
   

# Header: Current Case Information
st.header(f"Aktueller Fall ID: {st.session_state.current_case_id}")
if check_feedback_exists(st.session_state.current_case_id):
    st.markdown("<span style='color:red'>Für diesen Fall wurde bereits eine Bewertung gespeichert</span>", unsafe_allow_html=True)

# Row for Case Number Buttons
cases_per_row = 20  # Number of cases to display per row
num_rows = len(case_ids) // cases_per_row + (1 if len(case_ids) % cases_per_row else 0)

for row in range(num_rows):
    start = row * cases_per_row
    end = start + cases_per_row
    row_cases = case_ids[start:end]
    cols = st.columns(cases_per_row)
    for col, case_id in zip(cols, row_cases):
        with col:
            label = f"{case_id}"
            if check_feedback_exists(case_id):
                label += " 🔴"  # Red circle emoji to indicate feedback exists
            if st.button(label, key=f"case_{case_id}"):
                navigate_case(case_id)
                st.rerun()
                

# Kommentarfelder-Dictionary und Korrektheitsüberprüfung initialisieren
comments = {}
correctness = {}  # Dictionary für die Richtigkeit der Angaben

# Funktion zum Anzeigen eines Attributs mit einem Textfeld und einem Kommentarfeld
def display_attribute(key, value, prefix=''):
    display_value = str(value) if value not in [None, ""] else "kein Wert vorhanden"
    st.text_area(
    label=f"{attribute_names.get('involvedParties.'+key if 'involvedParties' in prefix else prefix+key, key)}",
    value=display_value,
    height=None,
    key=f"{prefix}{key}_display",
    disabled=True
    )

    # Single-Choice-Objekt für die Richtigkeit der Angaben mit Default auf "Ja"
    correctness_choice = st.radio("Angaben sind korrekt:", ('Ja', 'Nein'), index=0, key=f"{prefix}{key}_correctness")
    correctness[f"{prefix}{key}"] = correctness_choice == "Ja"  # Speichert True, wenn "Ja" ausgewählt wurde

    comments[f"{prefix}{key}"] = st.text_area(label="Kommentar", value='', key=f"{prefix}{key}_comment")

# Funktion zum Anzeigen der `involvedParties` nebeneinander in gleich großen Spalten
def display_involved_parties(involved_parties):
    if involved_parties:
        cols = st.columns(len(involved_parties))
        for i, party in enumerate(involved_parties):
            with cols[i]:
                st.subheader(f"Beteiligter {i+1}")
                for key, value in party.items():
                    display_attribute(key, value, prefix=f"involvedParties[{i}].")

# Funktion zum Anzeigen von `generalData` und `liabilityDecision`
def display_data_section(data_section, prefix):
    if data_section:
        for key, value in data_section.items():
            display_attribute(key, value, prefix=prefix)
# Anzeige der Daten
if data:
    st.header("Allgemeine Daten")
    display_data_section(data.get('generalData'), prefix='generalData.')
    
    st.header("Beteiligte")
    display_involved_parties(data.get('involvedParties'))
    
    st.header("Haftungsentscheidung")
    display_data_section(data.get('liabilityDecision'), prefix='liabilityDecision.')

    # Senden-Button zum Speichern der Kommentare und aktualisierten Daten
# Funktion zum Parsen des Pfads und Aktualisieren der Daten im verschachtelten Dictionary
def set_nested_value(d, path, value):
    keys = path.split('.')
    for key in keys[:-1]:
        if '[' in key and ']' in key:
            base_key, index_str = key[:-1].split('[')
            index = int(index_str)
            if base_key not in d or not isinstance(d[base_key], list):
                d[base_key] = []
            while len(d[base_key]) <= index:
                d[base_key].append({})
            d = d[base_key][index]
        else:
            if key not in d:
                d[key] = {}
            d = d[key]
    d[keys[-1]] = value

# 'Speichern'-Button-Callback
def save_data():
    # Aktuelle Daten kopieren
    updated_data = data.copy()
    
    # Alte '_id' entfernen, um ein neues Dokument einzufügen
    updated_data.pop('_id', None)

    # Kommentare und Korrektheit der Angaben hinzufügen
    for key, is_ok in correctness.items():
        # Kommentar und Korrektheitsstruktur vorbereiten
        comment = comments[key]
        # Den Pfad im verschachtelten Dictionary verfolgen und den letzten Schlüssel extrahieren
        keys = key.split('.')
        sub_data = updated_data
        for sub_key in keys[:-1]:  # Gehe durch die Schlüssel, außer den letzten
            if '[' in sub_key and ']' in sub_key:
                base_key, index_str = sub_key[:-1].split('[')
                index = int(index_str)
                sub_data = sub_data[base_key][index]
            else:
                sub_data = sub_data[sub_key]
        last_key = keys[-1]
        # Überprüfe, ob der letzte Schlüssel bereits ein Dictionary ist
        if not isinstance(sub_data[last_key], dict):
            sub_data[last_key] = {"value": sub_data[last_key]}  # Ursprünglichen Wert als 'value' speichern
        # Füge Kommentar und Korrektheit hinzu
        sub_data[last_key]["comment"] = comment
        sub_data[last_key]["isOk"] = is_ok
    
    # Das aktualisierte Dokument in die Feedback-Sammlung einfügen
    feedback_collection.insert_one(updated_data)
    st.success('Daten wurden erfolgreich gespeichert!')


# Verwenden Sie diese Funktion, wenn der Speichern-Button gedrückt wird
if st.button('Speichern'):
    save_data()
    st.rerun()
