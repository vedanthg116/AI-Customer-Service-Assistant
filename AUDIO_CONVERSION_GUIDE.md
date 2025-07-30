# Audio Conversion Guide for Azure Speech Service

Azure Speech Service works best with **WAV format (16-bit, 16kHz, mono)**. If you're having issues with MP3 or other audio formats, here's how to convert them:

## 🎯 Recommended WAV Format
- **Format**: WAV (Waveform Audio File Format)
- **Bit Depth**: 16-bit
- **Sample Rate**: 16kHz (16000 Hz)
- **Channels**: Mono (1 channel)
- **Encoding**: PCM

## 💻 Online Converters (Free)

### 1. **Convertio** (Recommended)
- **Website**: https://convertio.co/mp3-wav/
- **Steps**:
  1. Upload your MP3 file
  2. Select "WAV" as output format
  3. Click "Convert"
  4. Download the converted file

### 2. **Online Audio Converter**
- **Website**: https://online-audio-converter.com/
- **Steps**:
  1. Upload your audio file
  2. Choose "WAV" format
  3. Set quality to "16-bit, 16kHz, mono"
  4. Click "Convert"

### 3. **CloudConvert**
- **Website**: https://cloudconvert.com/mp3-to-wav
- **Steps**:
  1. Upload your file
  2. Select WAV output
  3. Download converted file

## 🖥️ Desktop Software

### **Audacity** (Free, Recommended)
1. **Download**: https://www.audacityteam.org/
2. **Install** and open Audacity
3. **Import** your audio file (File → Import → Audio)
4. **Export** as WAV:
   - File → Export → Export as WAV
   - Set format to "WAV (Microsoft) 16-bit PCM"
   - Set sample rate to 16000 Hz
   - Set channels to "Mono"

### **FFmpeg** (Command Line)
```bash
# Convert MP3 to WAV with optimal settings
ffmpeg -i input.mp3 -ar 16000 -ac 1 -acodec pcm_s16le output.wav
```

## 📱 Mobile Apps

### **iOS**
- **GarageBand**: Export as WAV
- **Voice Memos**: Already in compatible format

### **Android**
- **Smart Voice Recorder**: Set to WAV format
- **Audio Converter**: Available on Google Play

## 🔧 Quick Test

After converting, test your WAV file:
1. File size should be reasonable (not too large)
2. Should play in any audio player
3. Should work with Azure Speech Service

## ⚠️ Common Issues

### **File Too Large**
- Reduce sample rate to 16kHz
- Use mono instead of stereo
- Use 16-bit instead of 24-bit

### **Still Getting Errors**
- Ensure the file is actually WAV format (not just renamed)
- Check that the file isn't corrupted
- Try a different converter

### **No Sound After Conversion**
- Check that the original file had audio
- Try a different conversion method
- Verify the output file plays correctly

## 🎵 Sample Audio Creation

If you need to create test audio files:

### **Using Text-to-Speech**
1. Use Microsoft Azure Speech Service (https://speech.microsoft.com/audiocontentcreation)
2. Enter text and generate speech
3. Download as WAV format

### **Using Online TTS**
1. Google Text-to-Speech
2. Natural Reader
3. ElevenLabs

## 📋 Format Comparison

| Format | Azure Support | Quality | File Size |
|--------|---------------|---------|-----------|
| **WAV (16-bit, 16kHz, mono)** | ✅ **Best** | High | Medium |
| WAV (other settings) | ✅ Good | High | Large |
| MP3 | ⚠️ Limited | Good | Small |
| M4A | ❌ Poor | Good | Small |
| FLAC | ❌ Poor | Excellent | Large |

## 🚀 Next Steps

1. **Convert your audio file** to WAV format using one of the methods above
2. **Test the converted file** in your application
3. **Enjoy accurate speech-to-text transcription!** 🎉

---

**Need help?** Try converting your MP3 to WAV first, then test the WAV file in the application. 