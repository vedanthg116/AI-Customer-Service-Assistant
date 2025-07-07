# server/utils/sentiment_analyzer.py
from transformers import pipeline
import re # For simple regex-based entity extraction

# Initialize sentiment analysis pipeline (loaded once)
# You might need to specify 'device' if you have a GPU, e.g., device=0 for CUDA, device="mps" for Apple Silicon
try:
    sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    print("Sentiment Analysis pipeline loaded.")
except Exception as e:
    print(f"Error loading sentiment analysis pipeline: {e}")
    sentiment_pipeline = None

def get_sentiment(text: str):
    if sentiment_pipeline:
        return sentiment_pipeline(text)
    else:
        return [{"label": "unknown", "score": 0.0}]

# NEW FUNCTION: Basic Entity Extraction (can be replaced with more robust NLP)
def extract_entities(text: str):
    """
    A very basic entity extraction. For a real application, consider libraries
    like SpaCy (for Named Entity Recognition - NER) or more advanced regex.
    This example just looks for common patterns like numbers, dates (simple),
    and capitalized words that could be names/products.
    """
    entities = []

    # Example: Simple Product/Brand detection (capitalized words)
    # This is a very naive approach and will catch many non-entities.
    # For a real system, you'd have a list of known products/brands or use NER.
    capitalized_words = re.findall(r'\b[A-Z][a-zA-Z0-9]*\b', text)
    for word in capitalized_words:
        if len(word) > 1 and word.lower() not in ['i', 'a', 'the', 'is', 'and', 'but', 'or', 'for', 'on', 'with']: # rudimentary common word filter
            entities.append({"text": word, "label": "PRODUCT/BRAND (Naive)"})

    # Example: Phone numbers (simple pattern)
    phone_numbers = re.findall(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', text)
    for num in phone_numbers:
        entities.append({"text": num, "label": "PHONE_NUMBER"})

    # Example: Email addresses
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    for email in emails:
        entities.append({"text": email, "label": "EMAIL"})

    # You could extend this with more specific regex for other entity types,
    # or integrate with a proper NER library like SpaCy:
    # import spacy
    # nlp = spacy.load("en_core_web_sm")
    # doc = nlp(text)
    # for ent in doc.ents:
    #     entities.append({"text": ent.text, "label": ent.label_})

    return entities