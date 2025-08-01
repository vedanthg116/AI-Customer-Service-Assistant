import os
import sys
import subprocess
from pathlib import Path

# Install dependencies first
print("Installing dependencies...")
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Dependencies installed successfully!")
except Exception as e:
    print(f"Error installing dependencies: {e}")

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the FastAPI app
try:
    from main import app
    print("FastAPI app imported successfully!")
except Exception as e:
    print(f"Error importing FastAPI app: {e}")
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting FastAPI app on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port) 