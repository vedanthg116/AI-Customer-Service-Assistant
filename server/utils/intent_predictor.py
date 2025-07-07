# server/utils/intent_predictor.py
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from utils.text_processor import clean_text

class IntentPredictor:
    def __init__(self, models_dir="../models/"): # Default relative path for local testing
        self.models_dir = models_dir
        print(f"IntentPredictor: Attempting to load models from: {os.path.abspath(self.models_dir)}") # ADD THIS LINE
        self.vectorizer = self._load_model('tfidf_vectorizer.pkl')
        self.model = self._load_model('logistic_regression_model.pkl')
        self.label_encoder = self._load_model('label_encoder.pkl')
        print("IntentPredictor initialized and models loaded.")

    def _load_model(self, filename):
        file_path = os.path.join(self.models_dir, filename)
        print(f"  Attempting to load model file: {file_path}") # ADD THIS LINE
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Model file not found: {file_path}. Please ensure it's in the '{self.models_dir}' directory.")
        with open(file_path, 'rb') as f:
            return pickle.load(f)

    def predict_intent(self, text):

        cleaned_text = clean_text(text)
        text_tfidf = self.vectorizer.transform([cleaned_text])
        prediction_encoded = self.model.predict(text_tfidf)[0]
        prediction_proba = self.model.predict_proba(text_tfidf)[0]

        # Get the predicted label name
        predicted_label = self.label_encoder.inverse_transform([prediction_encoded])[0]
        # Get the confidence score for the predicted label
        confidence_score = prediction_proba[prediction_encoded]

        return predicted_label, float(confidence_score) # Return float for JSON serialization