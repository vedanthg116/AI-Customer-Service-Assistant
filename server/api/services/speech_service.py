# server/api/services/speech_service.py
import os
import asyncio
import tempfile
from typing import Optional
import azure.cognitiveservices.speech as speechsdk
from fastapi import UploadFile

class SpeechService:
    def __init__(self):
        # Get Azure Speech Service credentials from environment variables
        self.speech_key = os.getenv('AZURE_SPEECH_KEY')
        self.speech_region = os.getenv('AZURE_SPEECH_REGION')
        
        if not self.speech_key or not self.speech_region:
            print("Warning: Azure Speech Service credentials not found. Speech-to-text will not work.")
            print("Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION environment variables.")
    
    async def transcribe_audio_file(self, audio_file: UploadFile) -> Optional[str]:
        """
        Transcribe an audio file using Azure Speech Service.
        Returns the transcribed text or None if transcription fails.
        """
        if not self.speech_key or not self.speech_region:
            raise Exception("Azure Speech Service credentials not configured")
        
        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file.filename.split('.')[-1]}") as temp_file:
                content = await audio_file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            # Check file extension and provide guidance
            file_extension = audio_file.filename.split('.')[-1].lower()
            if file_extension not in ['wav']:
                print(f"Warning: File format '{file_extension}' may not be fully supported by Azure Speech Service.")
                print("For best results, use WAV format (16-bit, 16kHz, mono).")
            
            # Configure Azure Speech Service
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key, 
                region=self.speech_region
            )
            
            # Configure audio input - try different approaches based on file type
            if file_extension == 'wav':
                # For WAV files, use direct file input
                audio_config = speechsdk.AudioConfig(filename=temp_file_path)
            else:
                # For other formats, try using push audio stream
                # This is more flexible but requires reading the file as bytes
                try:
                    # First try direct file input (might work for some formats)
                    audio_config = speechsdk.AudioConfig(filename=temp_file_path)
                except Exception as e:
                    print(f"Direct file input failed for {file_extension}, trying alternative method: {e}")
                    # If that fails, we'll need to convert or use a different approach
                    raise Exception(f"Audio format '{file_extension}' is not supported. Please convert to WAV format (16-bit, 16kHz, mono).")
            
            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            # Perform transcription
            print(f"Transcribing audio file: {audio_file.filename}")
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                speech_recognizer.recognize_once
            )
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                transcription = result.text
                print(f"Transcription successful: {transcription[:100]}...")
                return transcription
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print(f"No speech detected in audio file: {result.no_match_details}")
                return None
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                print(f"Speech recognition canceled: {cancellation_details.reason}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    print(f"Error details: {cancellation_details.error_details}")
                    if "SPXERR_INVALID_HEADER" in str(cancellation_details.error_details):
                        raise Exception("Invalid audio file format. Please use WAV format (16-bit, 16kHz, mono) for best compatibility.")
                return None
            else:
                print(f"Unexpected result reason: {result.reason}")
                return None
                
        except Exception as e:
            print(f"Error during speech transcription: {str(e)}")
            # Clean up temporary file if it exists
            if 'temp_file_path' in locals():
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            raise e
    
    async def transcribe_audio_bytes(self, audio_bytes: bytes, file_extension: str = "wav") -> Optional[str]:
        """
        Transcribe audio bytes using Azure Speech Service.
        Useful for processing audio data directly from memory.
        """
        if not self.speech_key or not self.speech_region:
            raise Exception("Azure Speech Service credentials not configured")
        
        try:
            # Save bytes to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            # Configure Azure Speech Service
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key, 
                region=self.speech_region
            )
            
            # Configure audio input
            audio_config = speechsdk.AudioConfig(filename=temp_file_path)
            
            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            # Perform transcription
            print("Transcribing audio bytes...")
            result = await asyncio.get_event_loop().run_in_executor(
                None, 
                speech_recognizer.recognize_once
            )
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                transcription = result.text
                print(f"Transcription successful: {transcription[:100]}...")
                return transcription
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print(f"No speech detected in audio: {result.no_match_details}")
                return None
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                print(f"Speech recognition canceled: {cancellation_details.reason}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    print(f"Error details: {cancellation_details.error_details}")
                return None
            else:
                print(f"Unexpected result reason: {result.reason}")
                return None
                
        except Exception as e:
            print(f"Error during speech transcription: {str(e)}")
            # Clean up temporary file if it exists
            if 'temp_file_path' in locals():
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            raise e

# Create a singleton instance
speech_service = SpeechService() 