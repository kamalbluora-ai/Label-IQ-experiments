import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Find .env file in project root (parent of api/, core/, etc.)
project_root = Path(__file__).parent
load_dotenv(project_root / '.env')

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Handle GOOGLE_CREDENTIALS - convert relative path to absolute
_google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if _google_creds:
    creds_path = Path(_google_creds)
    if not creds_path.is_absolute():
        # Convert relative path to absolute from project root
        creds_path = project_root / _google_creds
    GOOGLE_CREDENTIALS = str(creds_path.resolve())
    # Update the environment variable to use absolute path
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_CREDENTIALS
else:
    # Fallback: look for google-credentials.json in project root
    default_path = project_root / 'google-credentials.json'
    if default_path.exists():
        GOOGLE_CREDENTIALS = str(default_path.resolve())
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_CREDENTIALS
    else:
        GOOGLE_CREDENTIALS = None