import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class Settings:
    # API Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Application Settings
    APP_NAME = os.getenv("APP_NAME", "QAAgent")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Test Configuration
    TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "30000"))
    HEADLESS_MODE = os.getenv("HEADLESS_MODE", "True").lower() == "true"
    BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")
    
    # Target Application
    TEST_EMAIL = os.getenv('RECRUTER_TEST_EMAIL', 'your-test-email@example.com')
    TEST_PASSWORD = os.getenv('RECRUTER_TEST_PASSWORD', 'your-test-password')
    RECRUTER_BASE_URL = os.getenv("RECRUTER_BASE_URL", "https://www.app.recruter.ai/")
    RECRUTER_SIGNUP_URL = os.getenv("RECRUTER_SIGNUP_URL", "https://www.recruter.ai/onboarding/Signup")
    
    # Base Directories
    PROJECT_ROOT = Path(__file__).parent.parent.resolve()   # Gets the root directory of your project
    PROJECT_ROOT_DATA = Path(__file__).parent.parent  # Gets the root directory of your project
    DATA_DIR = PROJECT_ROOT_DATA / "data"
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
    def get_reports_dir(cls, test_type: str = None) -> Path:
        """Get the reports directory, organized by test type (no timestamp)"""
        cls.ensure_directories()
        
        if test_type:
            reports_subdir = cls.REPORTS_DIR / test_type
            reports_subdir.mkdir(parents=True, exist_ok=True)
            return reports_subdir
        
        return cls.REPORTS_DIR
    
    @classmethod
    def get_screenshots_dir(cls, test_type: str = None) -> Path:
        """Get the screenshots directory, organized by test type (no timestamp)"""
        cls.ensure_directories()
        
        if test_type:
            screenshots_subdir = cls.SCREENSHOTS_BASE_DIR / test_type
            screenshots_subdir.mkdir(parents=True, exist_ok=True)
            return screenshots_subdir
        
        return cls.SCREENSHOTS_BASE_DIR
    
    @classmethod
    def get_videos_test_dir(cls, test_type: str = None) -> Path:
        """Get the videos directory, organized by test type (no timestamp)"""
        cls.ensure_directories()
        
        if test_type:
            videos_subdir = cls.VIDEOS_TEST_BASE_DIR / test_type
            videos_subdir.mkdir(parents=True, exist_ok=True)
            return videos_subdir
        
        return cls.VIDEOS_TEST_BASE_DIR
    
    @classmethod
    def get_test_case_dir(cls, test_name: str = None) -> Path:
        """Get the test case directory with consistent naming (no timestamp)"""
        cls.ensure_directories()
        
        if test_name:
            test_case_dir = cls.TEST_CASES_DIR / f"ts_{test_name}"
            test_case_dir.mkdir(parents=True, exist_ok=True)
            return test_case_dir
        
        return cls.TEST_CASES_DIR
    
    @classmethod
    def clear_directory_contents(cls, directory: Path, keep_subdirs: bool = False):
        """Clear all contents of a directory, optionally keeping subdirectories"""
        if not directory.exists():
            return
            
        for item in directory.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir() and not keep_subdirs:
                # Remove directory and all its contents
                import shutil
                shutil.rmtree(item)
    
    @classmethod
    def prepare_clean_directories(cls, test_type: str = "recruter_ai", clear_previous: bool = True):
        """Prepare directories for a new test run, optionally clearing previous results"""
        cls.ensure_directories()
        
        if clear_previous:
            # Clear previous test results
            reports_dir = cls.get_reports_dir(test_type)
            screenshots_dir = cls.get_screenshots_dir(test_type)
            videos_dir = cls.get_videos_test_dir(test_type)
            
            cls.clear_directory_contents(reports_dir)
            cls.clear_directory_contents(screenshots_dir)
            cls.clear_directory_contents(videos_dir)
        
        return {
            'tests_dir': str(cls.get_test_output_dir(test_type)),
            'reports_dir': str(cls.get_reports_dir(test_type)),
            'screenshots_dir': str(cls.get_screenshots_dir(test_type)),
            'videos_dir': str(cls.get_videos_test_dir(test_type)),
            'fixtures_dir': str(cls.FIXTURES_DIR)
        }
    
    @classmethod
    def get_playwright_config_paths(cls, test_type: str = "recruter_ai") -> dict:
        """Get all the paths needed for Playwright configuration (no timestamp)"""
        return cls.prepare_clean_directories(test_type, clear_previous=False)
    
    @classmethod
    def get_directory_structure(cls, test_type: str = "recruter_ai") -> dict:
        """Get the complete directory structure for a test type"""
        paths = cls.get_playwright_config_paths(test_type)
        
        return {
            'test_cases': str(cls.get_test_case_dir(test_type.replace('_', '.'))),
            'generated_tests': paths['tests_dir'],
            'reports': paths['reports_dir'],
            'screenshots': paths['screenshots_dir'],
            'videos': paths['videos_dir'],
            'fixtures': paths['fixtures_dir'],
            'transcripts': str(cls.TRANSCRIPTS_DIR),
            'vectorstore': str(cls.VECTORSTORE_DIR),
            'raw_videos': str(cls.VIDEOS_DIR)
        }
    
    # String path properties for backward compatibility and RAG engine
    @classmethod
    def get_vectorstore_path(cls) -> str:
        """Get vectorstore path as string for RAG engine compatibility"""
        cls.ensure_directories()
        return str(cls.VECTORSTORE_DIR)
    
    @classmethod
    def get_data_dir_path(cls) -> str:
        """Get data directory path as string"""
        cls.ensure_directories()
        return str(cls.DATA_DIR)
    
    @classmethod
    def get_transcripts_path(cls) -> str:
        """Get transcripts directory path as string"""
        cls.ensure_directories()
        return str(cls.TRANSCRIPTS_DIR)
    
    @classmethod
    def get_test_cases_path(cls) -> str:
        """Get test cases directory path as string"""
        cls.ensure_directories()
        return str(cls.TEST_CASES_DIR)
    
    @classmethod
    def get_videos_path(cls) -> str:
        """Get videos directory path as string"""
        cls.ensure_directories()
        return str(cls.VIDEOS_DIR)
    
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