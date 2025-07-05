import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

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
    
    # Base Directories
    PROJECT_ROOT = Path(__file__).parent.parent  # Gets the root directory of your project
    DATA_DIR = PROJECT_ROOT / "data"
    PLAYWRIGHT_BASE_DIR = PROJECT_ROOT / "playwright_tests"
    
    # Data Directories
    VIDEOS_DIR = DATA_DIR / "videos"
    TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
    TEST_CASES_DIR = DATA_DIR / "test_cases"
    VECTORSTORE_DIR = DATA_DIR / "vectorstore"
    
    # Playwright Test Directories
    TESTS_BASE_DIR = PLAYWRIGHT_BASE_DIR / "tests"
    GENERATED_TESTS_DIR = TESTS_BASE_DIR / "generated"
    REPORTS_DIR = TESTS_BASE_DIR / "reports"
    SCREENSHOTS_BASE_DIR = TESTS_BASE_DIR / "screenshots"
    VIDEOS_TEST_BASE_DIR = TESTS_BASE_DIR / "videos"
    FIXTURES_DIR = PLAYWRIGHT_BASE_DIR / "fixtures"
    
    # Specific Generated Test Subdirectories
    RECRUTER_TESTS_DIR = GENERATED_TESTS_DIR / "recruter_ai"
    CUSTOM_TESTS_DIR = GENERATED_TESTS_DIR / "custom"
    
    @classmethod
    def ensure_directories(cls):
        """Create all necessary directories if they don't exist"""
        base_directories = [
            cls.DATA_DIR,
            cls.VIDEOS_DIR,
            cls.TRANSCRIPTS_DIR,
            cls.TEST_CASES_DIR,
            cls.VECTORSTORE_DIR,
            cls.TESTS_BASE_DIR,
            cls.GENERATED_TESTS_DIR,
            cls.REPORTS_DIR,
            cls.SCREENSHOTS_BASE_DIR,
            cls.VIDEOS_TEST_BASE_DIR,
            cls.FIXTURES_DIR,
            cls.RECRUTER_TESTS_DIR,
            cls.CUSTOM_TESTS_DIR
        ]
        
        for directory in base_directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_test_output_dir(cls, test_type: str = "recruter_ai") -> Path:
        """Get the appropriate output directory for generated tests"""
        cls.ensure_directories()
        
        if test_type == "recruter_ai":
            return cls.RECRUTER_TESTS_DIR
        elif test_type == "custom":
            return cls.CUSTOM_TESTS_DIR
        else:
            # Create a new subdirectory for the test type
            custom_dir = cls.GENERATED_TESTS_DIR / test_type
            custom_dir.mkdir(parents=True, exist_ok=True)
            return custom_dir
    
    @classmethod
    def get_reports_dir(cls, test_type: str = None, with_timestamp: bool = True) -> Path:
        """Get the reports directory, organized by test type and optionally with timestamp"""
        cls.ensure_directories()
        
        if test_type:
            reports_subdir = cls.REPORTS_DIR / test_type
            reports_subdir.mkdir(parents=True, exist_ok=True)
            
            if with_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                timestamped_dir = reports_subdir / f"run_{timestamp}"
                timestamped_dir.mkdir(parents=True, exist_ok=True)
                return timestamped_dir
            
            return reports_subdir
        
        return cls.REPORTS_DIR
    
    @classmethod
    def get_screenshots_dir(cls, test_type: str = None, with_timestamp: bool = True) -> Path:
        """Get the screenshots directory, organized by test type and optionally with timestamp"""
        cls.ensure_directories()
        
        if test_type:
            screenshots_subdir = cls.SCREENSHOTS_BASE_DIR / test_type
            screenshots_subdir.mkdir(parents=True, exist_ok=True)
            
            if with_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                timestamped_dir = screenshots_subdir / f"run_{timestamp}"
                timestamped_dir.mkdir(parents=True, exist_ok=True)
                return timestamped_dir
            
            return screenshots_subdir
        
        return cls.SCREENSHOTS_BASE_DIR
    
    @classmethod
    def get_videos_test_dir(cls, test_type: str = None, with_timestamp: bool = True) -> Path:
        """Get the videos directory, organized by test type and optionally with timestamp"""
        cls.ensure_directories()
        
        if test_type:
            videos_subdir = cls.VIDEOS_TEST_BASE_DIR / test_type
            videos_subdir.mkdir(parents=True, exist_ok=True)
            
            if with_timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                timestamped_dir = videos_subdir / f"run_{timestamp}"
                timestamped_dir.mkdir(parents=True, exist_ok=True)
                return timestamped_dir
            
            return videos_subdir
        
        return cls.VIDEOS_TEST_BASE_DIR
    
    @classmethod
    def get_test_case_dir(cls, test_name: str = None, with_timestamp: bool = True) -> Path:
        """Get the test case directory with consistent naming"""
        cls.ensure_directories()
        
        if test_name and with_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            test_case_dir = cls.TEST_CASES_DIR / f"ts_{test_name}_{timestamp}"
            test_case_dir.mkdir(parents=True, exist_ok=True)
            return test_case_dir
        elif test_name:
            test_case_dir = cls.TEST_CASES_DIR / f"ts_{test_name}"
            test_case_dir.mkdir(parents=True, exist_ok=True)
            return test_case_dir
        
        return cls.TEST_CASES_DIR
    
    @classmethod
    def get_playwright_config_paths(cls, test_type: str = "recruter_ai") -> dict:
        """Get all the paths needed for Playwright configuration"""
        cls.ensure_directories()
        
        # Use current timestamp for this test run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return {
            'tests_dir': str(cls.get_test_output_dir(test_type)),
            'reports_dir': str(cls.get_reports_dir(test_type, with_timestamp=True)),
            'screenshots_dir': str(cls.get_screenshots_dir(test_type, with_timestamp=True)),
            'videos_dir': str(cls.get_videos_test_dir(test_type, with_timestamp=True)),
            'fixtures_dir': str(cls.FIXTURES_DIR),
            'timestamp': timestamp
        }
    
    @classmethod
    def get_directory_structure(cls, test_type: str = "recruter_ai") -> dict:
        """Get the complete directory structure for a test type"""
        paths = cls.get_playwright_config_paths(test_type)
        
        return {
            'test_cases': str(cls.get_test_case_dir(test_type.replace('_', '.'), with_timestamp=True)),
            'generated_tests': paths['tests_dir'],
            'reports': paths['reports_dir'],
            'screenshots': paths['screenshots_dir'],
            'videos': paths['videos_dir'],
            'fixtures': paths['fixtures_dir'],
            'transcripts': str(cls.TRANSCRIPTS_DIR),
            'vectorstore': str(cls.VECTORSTORE_DIR),
            'raw_videos': str(cls.VIDEOS_DIR)
        }
    
    # Legacy properties for backward compatibility
    @property
    def SCREENSHOTS_DIR(self) -> Path:
        """Legacy property - use get_screenshots_dir() instead"""
        return self.SCREENSHOTS_BASE_DIR
    
    @property
    def VIDEOS_TEST_DIR(self) -> Path:
        """Legacy property - use get_videos_test_dir() instead"""
        return self.VIDEOS_TEST_BASE_DIR

settings = Settings()