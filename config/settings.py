import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    
    # Application Settings
    APP_NAME = os.getenv("APP_NAME", "QAAgent")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Test Configuration
    TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "30000"))
    HEADLESS_MODE = os.getenv("HEADLESS_MODE", "True").lower() == "true"
    BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")
    
    # Target Application
    RECRUTER_BASE_URL = os.getenv("RECRUTER_BASE_URL", "https://www.recruter.ai")
    RECRUTER_SIGNUP_URL = os.getenv("RECRUTER_SIGNUP_URL", "https://www.recruter.ai/onboarding/Signup")
    
    # Directories
    DATA_DIR = "data"
    VIDEOS_DIR = f"{DATA_DIR}/videos"
    TRANSCRIPTS_DIR = f"{DATA_DIR}/transcripts"
    TEST_CASES_DIR = f"{DATA_DIR}/test_cases"
    VECTORSTORE_DIR = f"{DATA_DIR}/vectorstore"
    REPORTS_DIR = "tests/reports"
    SCREENSHOTS_DIR = "tests/screenshots"

settings = Settings()