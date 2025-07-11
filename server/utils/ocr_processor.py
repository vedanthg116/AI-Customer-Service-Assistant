# server/utils/ocr_processor.py
import easyocr
import numpy as np
import cv2
import os

# Initialize EasyOCR reader once when the module is loaded.
# This downloads language models if not present, so it might take a moment on first run.
# 'en' for English. You can add more languages like ['en', 'hi'] for Hindi, etc.
# gpu=False to force CPU usage, which is common for local development without a dedicated GPU.
try:
    # Set the EasyOCR model directory to a local path to avoid issues with default locations
    # and ensure models are saved within the project if desired.
    # For simplicity, let's keep it in the default user home directory for now,
    # as setting a custom path can sometimes lead to permissions issues.
    # If you encounter "OSError: [Errno 13] Permission denied" related to models,
    # you might need to specify reader = easyocr.Reader(['en'], model_storage_directory='.')
    # and ensure that directory is writable.
    reader = easyocr.Reader(['en'], gpu=False)
    print("EasyOCR reader initialized with English language model (CPU mode).")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to initialize EasyOCR reader. Error: {e}")
    reader = None # Set to None if initialization fails


async def detect_text_from_image(image_bytes: bytes) -> str:
    """
    Detects text from the given image bytes using EasyOCR.

    Args:
        image_bytes: The byte content of the image.

    Returns:
        A string containing all detected text, or an empty string if no text is found
        or if the EasyOCR reader failed to initialize/process.
    """
    if not reader:
        print("EasyOCR reader not available. Cannot perform OCR.")
        return "OCR Service Unavailable (EasyOCR not initialized)"

    try:
        # Convert image bytes to a NumPy array
        np_array = np.frombuffer(image_bytes, np.uint8)
        # Decode the image using OpenCV
        image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

        if image is None:
            print("Failed to decode image bytes. It might be corrupted or an unsupported format.")
            return "Image decoding failed"

        # Perform OCR
        # reader.readtext returns a list of (bbox, text, prob)
        results = reader.readtext(image)

        detected_texts = [text for (bbox, text, prob) in results]
        full_text = "\n".join(detected_texts) # Join all detected text lines

        if full_text:
            print(f"EasyOCR detected text (first 100 chars): {full_text[:100]}...")
            return full_text
        else:
            print("No text detected in image by EasyOCR.")
            return ""
    except Exception as e:
        print(f"Error during OCR with EasyOCR: {e}")
        return f"OCR Error (EasyOCR): {e}"