# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

def get_api_key():
    """
    Retrieves the API key stored in the environment variable 'GOOGLE_API_KEY'.
    Raises ValueError if not set.
    """
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        raise ValueError("API key 'GOOGLE_API_KEY' not found. Please set it in the .env file or environment variables.")
    return key
