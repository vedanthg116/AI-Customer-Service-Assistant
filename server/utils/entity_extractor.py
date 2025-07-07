# server/utils/entity_extractor.py
import spacy
import os

_nlp_model = None # Private variable to hold the loaded SpaCy model

def load_spacy_model():
    global _nlp_model
    if _nlp_model is None:
        try:
            # Ensure the model is downloaded. If not, user needs to run:
            # python -m spacy download en_core_web_sm
            _nlp_model = spacy.load("en_core_web_sm")
            print("SpaCy model 'en_core_web_sm' loaded successfully.")
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to load SpaCy model: {e}")
            print("Please ensure you've run 'python -m spacy download en_core_web_sm'")
            _nlp_model = None
    return _nlp_model

def extract_entities(text: str) -> list:
    nlp = load_spacy_model()
    if nlp:
        doc = nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start_char": ent.start_char,
                "end_char": ent.end_char
            })
        return entities
    return []

# Call load_spacy_model() here so it attempts to load when the module is imported
# This makes sure the model is loaded when the FastAPI app starts
load_spacy_model()