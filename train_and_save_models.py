import pandas as pd
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import re
import pickle
import os

print("Starting model training and saving process...")

# --- 1. Load the dataset ---
# Load the full 'train' split for comprehensive training
try:
    full_original_dataset = load_dataset("bitext/Bitext-customer-support-llm-chatbot-training-dataset")
    df = full_original_dataset['train'].to_pandas()
    print(f"Dataset loaded. Total rows: {len(df)}")
except Exception as e:
    print(f"Error loading dataset: {e}")
    print("Please ensure you have 'datasets' and 'pyarrow' installed ('pip install datasets pyarrow').")
    exit() # Exit if data can't be loaded

# --- 2. Text Cleaning Function ---
def clean_text(text):
    text = text.lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Apply cleaning to instructions
df['cleaned_instruction'] = df['instruction'].apply(clean_text)
print("Text cleaning complete.")

# --- 3. Split Data (Optional for saving, but good practice for evaluation) ---
# We'll train on the 'cleaned_instruction' and 'intent' columns
X = df['cleaned_instruction']
y = df['intent']

# Although we'll train on the full 'train' set for the final model,
# you might want a small split here for evaluation if you haven't done it before.
# For simplicity for this save script, we'll use the full X, y to fit the vectorizer and model.

# --- 4. Initialize and Fit TF-IDF Vectorizer ---
tfidf_vectorizer = TfidfVectorizer(max_features=5000) # You can adjust max_features
X_tfidf = tfidf_vectorizer.fit_transform(X)
print(f"TF-IDF Vectorizer fitted. Number of features: {X_tfidf.shape[1]}")

# --- 5. Initialize and Fit Label Encoder ---
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
print(f"Label Encoder fitted. {len(label_encoder.classes_)} unique intents found.")

# --- 6. Train the Logistic Regression Model ---
log_reg_model = LogisticRegression(max_iter=1000, random_state=42) # Increased max_iter for convergence
log_reg_model.fit(X_tfidf, y_encoded)
print("Logistic Regression model trained.")

# --- 7. Save the Trained Models and Artifacts ---
# Define the path to your models directory relative to where this script will be run.
# Assuming you run this from your project root: your_ai_assistant_project/
models_save_dir = './server/models/'

# Create the models directory if it doesn't exist
os.makedirs(models_save_dir, exist_ok=True)
print(f"Ensuring models directory exists at: {os.path.abspath(models_save_dir)}")

# Save the TF-IDF Vectorizer
with open(os.path.join(models_save_dir, 'tfidf_vectorizer.pkl'), 'wb') as f:
    pickle.dump(tfidf_vectorizer, f)
print(f"Saved TF-IDF Vectorizer to {os.path.join(models_save_dir, 'tfidf_vectorizer.pkl')}")

# Save the Logistic Regression Model
with open(os.path.join(models_save_dir, 'logistic_regression_model.pkl'), 'wb') as f:
    pickle.dump(log_reg_model, f)
print(f"Saved Logistic Regression Model to {os.path.join(models_save_dir, 'logistic_regression_model.pkl')}")

# Save the Label Encoder
with open(os.path.join(models_save_dir, 'label_encoder.pkl'), 'wb') as f:
    pickle.dump(label_encoder, f)
print(f"Saved Label Encoder to {os.path.join(models_save_dir, 'label_encoder.pkl')}")

print("\nAll models and artifacts saved successfully! You can now start your FastAPI server.")