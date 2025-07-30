# Azure Speech Service Setup Guide

This guide will help you set up Azure Speech Service for the speech-to-text functionality in the customer service application.

## Prerequisites
- Azure Student Account (you have this!)
- Python 3.8+ installed

## Step 1: Create Azure Speech Service Resource

1. **Go to Azure Portal**: https://portal.azure.com
2. **Search for "Speech Service"** in the search bar
3. **Click "Create"** to create a new Speech Service resource
4. **Fill in the details**:
   - **Subscription**: Your student subscription
   - **Resource Group**: Create new or use existing
   - **Region**: Choose a region close to you (e.g., East US, West Europe)
   - **Name**: Give it a unique name (e.g., `my-speech-service`)
   - **Pricing Tier**: Choose "Free (F0)" for student account (limited but sufficient for testing)
5. **Click "Review + Create"** then **"Create"**

## Step 2: Get Your Credentials

1. **Go to your Speech Service resource** in Azure Portal
2. **Click on "Keys and Endpoint"** in the left sidebar
3. **Copy Key 1** and **Region** (you'll need both)

## Step 3: Configure Environment Variables

1. **Create or edit your `.env` file** in the `server` directory:
   ```bash
   # Existing variables...
   GEMINI_API_KEY="your_gemini_key"
   
   # Add these new variables:
   AZURE_SPEECH_KEY="your_azure_speech_key_here"
   AZURE_SPEECH_REGION="your_azure_region_here"
   ```

2. **Replace the values**:
   - `your_azure_speech_key_here`: The Key 1 you copied from Azure
   - `your_azure_region_here`: The region you copied (e.g., "eastus", "westeurope")

## Step 4: Install Dependencies

1. **Navigate to the server directory**:
   ```bash
   cd server
   ```

2. **Install the Azure Speech SDK**:
   ```bash
   pip install azure-cognitiveservices-speech==1.34.0
   ```

3. **Or install all requirements**:
   ```bash
   pip install -r requirements.txt
   ```

## Step 5: Test the Setup

1. **Start the backend server**:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

2. **Check the logs** - you should see:
   ```
   Azure Speech Service credentials loaded successfully
   ```

3. **Test the functionality**:
   - Go to the Agent Dashboard
   - Click "Process Recorded Call"
   - Upload an audio file (WAV, MP3, M4A, FLAC, or OGG)
   - The system should transcribe it and show the results

## Supported Audio Formats

- **WAV** (recommended for best quality)
- **MP3**
- **M4A**
- **FLAC**
- **OGG**

## File Size Limits

- **Maximum file size**: 50MB
- **Recommended**: Keep files under 10MB for faster processing

## Troubleshooting

### "Azure Speech Service credentials not configured"
- Check that your `.env` file has the correct variables
- Restart the server after adding environment variables
- Verify the key and region are correct

### "No speech detected in audio file"
- Ensure the audio file contains clear speech
- Check that the file format is supported
- Try a different audio file

### "Transcription failed"
- Check your Azure Speech Service quota (Free tier has limits)
- Verify your Azure subscription is active
- Check the Azure Portal for any service issues

## Cost Considerations

- **Free Tier (F0)**: 5 hours of audio per month
- **Standard Tier**: Pay per hour of audio processed
- **Student Account**: Usually includes free credits

## Security Notes

- Never commit your Azure keys to version control
- Use environment variables for all sensitive data
- Consider using Azure Key Vault for production deployments

## Next Steps

Once set up, you can:
1. Upload recorded call audio files
2. Get automatic speech-to-text transcription
3. Receive AI analysis (intent, sentiment, entities)
4. Process the results in your customer service workflow

Happy coding! 🎤✨ 