import os
import json
import subprocess
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import asyncio
import time
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from dataclasses import dataclass
from enum import Enum
from agents.base_agent import BaseAgent
from models.test_case import AgentResponse, TestResult, TestStatus, TestSuiteResult
from utils.file_utils import save_json, load_json
from config.settings import settings

logger = logging.getLogger(__name__)

class TestExecutionAgent(BaseAgent):
    """Agent responsible for executing generated Playwright tests"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("TestExecutionAgent", config)
        
        # Ensure directories exist
        settings.ensure_directories()
        
        # Configuration
        self.base_url = self.get_config('base_url', settings.RECRUTER_BASE_URL)
        self.headless = self.get_config('headless', True)
        self.browser = self.get_config('browser', 'chromium')  # chromium, firefox, webkit
        self.timeout = self.get_config('timeout', 30000)  # 30 seconds
        self.video_enabled = self.get_config('video_enabled', True)
        self.screenshot_enabled = self.get_config('screenshot_enabled', True)
        self.retries = self.get_config('retries', 2)
        self.parallel_workers = self.get_config('parallel_workers', 1)
        
        self.test_type = self.get_config('test_type', 'recruter_ai')
    
        # Use dynamic directory methods
        self.test_scripts_dir = settings.get_test_output_dir(self.test_type)
        self.reports_dir = settings.get_reports_dir(self.test_type, with_timestamp=False)
        self.screenshots_dir = settings.get_screenshots_dir(self.test_type, with_timestamp=False)
        self.videos_dir = settings.get_videos_test_dir(self.test_type, with_timestamp=False)
        
        # Ensure all directories exist
        for directory in [self.test_scripts_dir, self.reports_dir, self.screenshots_dir, self.videos_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Execution statistics
        self.stats = {
            'total_executions': 0,
            'total_tests_run': 0,
            'total_passed': 0,
            'total_failed': 0,
            'total_errors': 0,
            'last_execution': None,
            'execution_history': []
        }
        
        self.logger.info("TestExecutionAgent initialized")
        self.logger.info(f"Test scripts directory: {self.test_scripts_dir}")
        self.logger.info(f"Reports directory: {self.reports_dir}")
    
    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Main processing method for test execution
        
        Args:
            input_data: Dict containing:
                - test_suite_path: Path to test suite directory or specific test files
                - test_type: Type of tests to run (e.g., 'recruter_ai')
                - execution_config: Optional execution configuration overrides
        """
        try:
            # Validate input
            if not isinstance(input_data, dict):
                return self.create_error_response("Input must be a dictionary")
            
            test_suite_path = input_data.get('test_suite_path')
            test_type = input_data.get('test_type', 'recruter_ai')
            execution_config = input_data.get('execution_config', {})
            
            # If no specific path provided, use the test type directory
            if not test_suite_path:
                test_suite_path = settings.get_test_output_dir(test_type)
            
            test_suite_path = Path(test_suite_path)
            
            if not test_suite_path.exists():
                return self.create_error_response(f"Test suite path does not exist: {test_suite_path}")
            
            # Execute tests
            execution_result = self.execute_test_suite(test_suite_path, test_type, execution_config)
            
            # Generate report
            report_path = self.generate_execution_report(execution_result)
            execution_result.report_path = str(report_path)
            
            # Update statistics
            self.update_stats(execution_result)
            
            self.log_operation(
                "test_execution_completed",
                {
                    'suite_id': execution_result.suite_id,
                    'total_tests': execution_result.total_tests,
                    'passed': execution_result.passed,
                    'failed': execution_result.failed,
                    'duration': execution_result.total_duration,
                    'test_type': test_type
                }
            )
            
            return self.create_success_response(
                f"Test execution completed: {execution_result.passed}/{execution_result.total_tests} tests passed",
                {
                    'execution_result': self._serialize_execution_result(execution_result),
                    'report_path': str(report_path),
                    'artifacts_dir': execution_result.artifacts_dir,
                    'test_type': test_type
                }
            )
            
        except Exception as e:
            error_msg = f"Test execution failed: {str(e)}"
            self.logger.error(error_msg)
            return self.create_error_response(error_msg)
    
    def execute_test_suite(self, test_suite_path: Path, test_type: str, 
                          execution_config: Dict[str, Any] = None) -> TestSuiteResult:
        """Execute a test suite and return results"""
        try:
            start_time = datetime.now()
            
            # Find test files
            test_files = self._find_test_files(test_suite_path)
            if not test_files:
                raise ValueError(f"No test files found in {test_suite_path}")
            
            # Create execution-specific artifacts directory
            execution_id = f"exec_{test_type}_{start_time.strftime('%Y%m%d_%H%M%S')}"
            artifacts_dir = self.reports_dir / execution_id
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Setup execution environment
            env = self._setup_execution_environment(artifacts_dir, execution_config)
            
            # Execute tests
            test_results = []
            for test_path in test_files:  # Now test_files contains directories
                if test_path.is_dir():
                    self.logger.info(f"Executing test directory: {test_path}")
                else:
                    self.logger.info(f"Executing test file: {test_path}")
                
                result = self._execute_single_test_file(test_path, artifacts_dir, env)
                test_results.extend(result)
            
            end_time = datetime.now()
            
            # Calculate summary statistics
            passed = sum(1 for r in test_results if r.status == TestStatus.PASSED)
            failed = sum(1 for r in test_results if r.status == TestStatus.FAILED)
            skipped = sum(1 for r in test_results if r.status == TestStatus.SKIPPED)
            errors = sum(1 for r in test_results if r.status == TestStatus.ERROR)
            total_duration = (end_time - start_time).total_seconds()
            
            # Create test suite result
            suite_result = TestSuiteResult(
                suite_id=execution_id,
                suite_name=f"Test Suite - {test_type}",
                total_tests=len(test_results),
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                total_duration=total_duration,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                test_results=test_results,
                artifacts_dir=str(artifacts_dir)
            )
            
            self.logger.info(f"Test suite execution completed: {passed}/{len(test_results)} tests passed")
            
            return suite_result
            
        except Exception as e:
            self.logger.error(f"Error executing test suite: {e}")
            raise
    
    def _setup_execution_environment(self, artifacts_dir: Path, 
                               execution_config: Dict[str, Any] = None) -> Dict[str, str]:
        """Setup environment variables for test execution"""
        config = execution_config or {}
        
        # Get Playwright paths from settings for this test type
        playwright_paths = settings.get_playwright_config_paths(self.test_type)
        
        # Base environment
        env = os.environ.copy()
        
        # Playwright specific settings
        env['PLAYWRIGHT_BROWSERS_PATH'] = str(Path.home() / '.cache' / 'ms-playwright')
        
        # Use timestamped directories from settings for this execution
        screenshots_dir = Path(playwright_paths['screenshots_dir'])
        videos_dir = Path(playwright_paths['videos_dir'])
        reports_dir = Path(playwright_paths['reports_dir'])
        
        # Override with execution-specific artifacts directory if needed
        if artifacts_dir != reports_dir:
            screenshots_dir = artifacts_dir / 'screenshots'
            videos_dir = artifacts_dir / 'videos'
        
        env['PLAYWRIGHT_SCREENSHOTS_DIR'] = str(screenshots_dir)
        env['PLAYWRIGHT_VIDEOS_DIR'] = str(videos_dir)
        env['PLAYWRIGHT_REPORTS_DIR'] = str(reports_dir)
        
        # Test configuration from settings and overrides
        env['BASE_URL'] = config.get('base_url', self.base_url)
        env['RECRUTER_BASE_URL'] = config.get('base_url', self.base_url)
        env['RECRUTER_SIGNUP_URL'] = config.get('signup_url', settings.RECRUTER_SIGNUP_URL)
        env['TEST_EMAIL'] = config.get('test_email', settings.TEST_EMAIL)
        env['TEST_PASSWORD'] = config.get('test_password', settings.TEST_PASSWORD)
        
        # Browser configuration
        env['HEADLESS'] = str(config.get('headless', self.headless)).lower()
        env['BROWSER'] = config.get('browser', self.browser)
        env['BROWSER_TYPE'] = config.get('browser', self.browser)
        
        # Timeouts and retries
        env['TIMEOUT'] = str(config.get('timeout', self.timeout))
        env['TEST_TIMEOUT'] = str(config.get('timeout', self.timeout))
        env['RETRIES'] = str(config.get('retries', self.retries))
        
        # Test execution settings
        env['PARALLEL_WORKERS'] = str(config.get('parallel_workers', self.parallel_workers))
        env['VIDEO_ENABLED'] = str(config.get('video_enabled', self.video_enabled)).lower()
        env['SCREENSHOT_ENABLED'] = str(config.get('screenshot_enabled', self.screenshot_enabled)).lower()
        
        # Debug and logging
        env['DEBUG'] = str(config.get('debug', settings.DEBUG)).lower()
        env['LOG_LEVEL'] = config.get('log_level', settings.LOG_LEVEL)
        
        # Test type and execution context
        env['TEST_TYPE'] = self.test_type
        env['EXECUTION_ID'] = artifacts_dir.name
        env['TIMESTAMP'] = playwright_paths['timestamp']
        
        # Playwright specific environment variables
        env['PWTEST_SKIP_TEST_OUTPUT'] = 'false'
        env['PWTEST_HTML_REPORT_OPEN'] = 'never'
        
        # Create all necessary subdirectories
        directories_to_create = [
            screenshots_dir,
            videos_dir,
            reports_dir,
            artifacts_dir / 'traces',
            artifacts_dir / 'test-results'
        ]
        
        for directory in directories_to_create:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Log the environment setup
        self.logger.info(f"Environment setup for test type: {self.test_type}")
        self.logger.info(f"Screenshots dir: {screenshots_dir}")
        self.logger.info(f"Videos dir: {videos_dir}")
        self.logger.info(f"Reports dir: {reports_dir}")
        self.logger.info(f"Base URL: {env['BASE_URL']}")
        self.logger.info(f"Browser: {env['BROWSER']} (headless: {env['HEADLESS']})")
        
        return env
    
    def _find_test_files(self, test_suite_path: Path) -> List[Path]:
        """Find all test directories or files"""
        test_paths = []
        
        if test_suite_path.is_file() and test_suite_path.suffix in ['.js', '.ts']:
            test_paths.append(test_suite_path)
        elif test_suite_path.is_dir():
            # Look for test directories first (performance, edge_cases, etc.)
            test_dirs = ['performance', 'edge_cases', 'accessibility', 'functionality', 'cross_browser']
            
            for test_dir in test_dirs:
                dir_path = test_suite_path / test_dir
                if dir_path.exists() and dir_path.is_dir():
                    # Get all test files in this directory
                    test_files = list(dir_path.glob('*.spec.ts')) + list(dir_path.glob('*.test.ts'))
                    if test_files:
                        # Add individual test files, not the directory
                        test_paths.extend(test_files)
            
            # If no test directories found, look for individual test files in the root
            if not test_paths:
                test_patterns = ['*.test.ts', '*.spec.ts', '*-test.ts', '*-spec.ts']
                for pattern in test_patterns:
                    test_paths.extend(test_suite_path.rglob(pattern))
        
        # Remove duplicates and sort
        unique_paths = sorted(list(set(test_paths)))
        
        self.logger.info(f"Found {len(unique_paths)} test files in {test_suite_path}")
        for path in unique_paths:
            self.logger.info(f"  - {path}")
        
        return unique_paths

    def _execute_single_test_file(self, test_path: Path, artifacts_dir: Path, 
                            env: Dict[str, str]) -> List[TestResult]:
        """Execute a single test file and return results"""
        try:
            # Normalize paths to absolute resolved form
            project_root = Path(__file__).parent.parent.resolve()
            playwright_dir = (project_root / 'playwright_tests').resolve()
            test_path = test_path.resolve()

            # Safe relative path
            relative_test_path = test_path.relative_to(playwright_dir)

            # Prepare Playwright command
            cmd = [
                'npx.cmd', 'playwright', 'test',
                str(relative_test_path),  # Use relative path to the specific test file
                '--reporter=json',
                f'--output-dir={artifacts_dir}',
                '--headed' if not self.headless else '--headless',
                f'--browser={self.browser}',
                f'--timeout={self.timeout}',
                f'--retries={self.retries}'
            ]
            
            # Add video recording if enabled
            if self.video_enabled:
                cmd.extend(['--video=retain-on-failure'])
            
            # Add screenshot on failure
            if self.screenshot_enabled:
                cmd.extend(['--screenshot=only-on-failure'])
            
            self.logger.info(f"Executing test file: {test_path.name}")
            self.logger.info(f"Relative path: {relative_test_path}")
            self.logger.info(f"Working directory: {playwright_dir}")
            self.logger.info(f"Command: {' '.join(cmd)}")
            
            # Execute the test
            result = subprocess.run(
                cmd,
                cwd=playwright_dir,  # Use playwright_tests as working directory
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            self.logger.info(f"Test execution completed. Return code: {result.returncode}")
            if result.stdout:
                self.logger.debug(f"STDOUT: {result.stdout}")
            if result.stderr:
                self.logger.debug(f"STDERR: {result.stderr}")
            
            # Parse results
            test_results = self._parse_playwright_results(result, test_path, artifacts_dir)
            
            return test_results
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Test execution timed out for {test_path}")
            return [TestResult(
                test_id=f"timeout_{test_path.name}",
                test_name=test_path.name,
                status=TestStatus.ERROR,
                duration=300.0,
                error_message="Test execution timed out"
            )]
        except FileNotFoundError as e:
            self.logger.error(f"File not found error: {e}")
            return [TestResult(
                test_id=f"file_not_found_{test_path.name}",
                test_name=test_path.name,
                status=TestStatus.ERROR,
                duration=0.0,
                error_message=f"File not found: {str(e)}"
            )]
        except Exception as e:
            self.logger.error(f"Error executing test file {test_path}: {e}")
            return [TestResult(
                test_id=f"error_{test_path.name}",
                test_name=test_path.name,
                status=TestStatus.ERROR,
                duration=0.0,
                error_message=str(e)
            )]
    
    def _execute_single_test_file_with_retry(self, test_file: Path, artifacts_dir: Path, 
                                        env: Dict[str, str]) -> List[TestResult]:
        """Execute test file with retry logic"""
        max_retries = self.retries
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"Retrying test execution for {test_file.name} (attempt {attempt + 1})")
                
                return self._execute_single_test_file(test_file, artifacts_dir, env)
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Test execution attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        # All retries failed
        return [TestResult(
            test_id=f"retry_failed_{test_file.name}",
            test_name=test_file.name,
            status=TestStatus.ERROR,
            duration=0.0,
            error_message=f"All {max_retries + 1} attempts failed. Last error: {str(last_exception)}",
            retry_count=max_retries
        )]
    
    def _parse_playwright_results(self, subprocess_result: subprocess.CompletedProcess, 
                                 test_file: Path, artifacts_dir: Path) -> List[TestResult]:
        """Parse Playwright test results from subprocess output"""
        try:
            test_results = []
            
            # Try to parse JSON output first
            try:
                if subprocess_result.stdout:
                    # Look for JSON in stdout
                    lines = subprocess_result.stdout.split('\n')
                    for line in lines:
                        if line.strip().startswith('{') and 'suites' in line:
                            json_data = json.loads(line)
                            return self._parse_playwright_json_results(json_data, artifacts_dir)
                
                output = subprocess_result.stdout + subprocess_result.stderr
                if 'login' in output.lower() and 'failed' in output.lower():
                    return [TestResult(
                        test_id=f"auth_failed_{test_file.name}",
                        test_name=test_file.name,
                        status=TestStatus.ERROR,
                        duration=0.0,
                        error_message="Authentication failed - check credentials"
                    )]
            except json.JSONDecodeError:
                pass
            
            # Fallback to parsing text output
            return self._parse_playwright_text_results(subprocess_result, test_file, artifacts_dir)
            
        except Exception as e:
            self.logger.error(f"Error parsing Playwright results: {e}")
            return [TestResult(
                test_id=f"parse_error_{test_file.name}",
                test_name=test_file.name,
                status=TestStatus.ERROR,
                duration=0.0,
                error_message=f"Failed to parse results: {str(e)}"
            )]
    
    def _parse_playwright_json_results(self, json_data: Dict[str, Any], 
                                      artifacts_dir: Path) -> List[TestResult]:
        """Parse Playwright JSON results"""
        test_results = []
        
        try:
            for suite in json_data.get('suites', []):
                for spec in suite.get('specs', []):
                    for test in spec.get('tests', []):
                        test_id = test.get('id', 'unknown')
                        test_name = test.get('title', 'Unknown Test')
                        
                        # Get test status
                        status = TestStatus.PASSED
                        error_message = None
                        duration = 0.0
                        
                        for result in test.get('results', []):
                            duration += result.get('duration', 0) / 1000.0  # Convert to seconds
                            
                            if result.get('status') == 'failed':
                                status = TestStatus.FAILED
                                error_message = result.get('error', {}).get('message', 'Test failed')
                            elif result.get('status') == 'skipped':
                                status = TestStatus.SKIPPED
                        
                        # Find artifacts
                        screenshot_path = self._find_test_artifacts(test_id, artifacts_dir, 'screenshot')
                        video_path = self._find_test_artifacts(test_id, artifacts_dir, 'video')
                        
                        test_results.append(TestResult(
                            test_id=test_id,
                            test_name=test_name,
                            status=status,
                            duration=duration,
                            error_message=error_message,
                            screenshot_path=screenshot_path,
                            video_path=video_path
                        ))
            
        except Exception as e:
            self.logger.error(f"Error parsing JSON results: {e}")
        
        return test_results
    
    def _parse_playwright_text_results(self, subprocess_result: subprocess.CompletedProcess, 
                                      test_file: Path, artifacts_dir: Path) -> List[TestResult]:
        """Parse Playwright text output as fallback"""
        try:
            # Simple fallback parsing
            output = subprocess_result.stdout + subprocess_result.stderr
            
            # Determine overall status
            if subprocess_result.returncode == 0:
                status = TestStatus.PASSED
                error_message = None
            else:
                status = TestStatus.FAILED
                error_message = subprocess_result.stderr or "Test failed"
            
            return [TestResult(
                test_id=f"text_{test_file.stem}",
                test_name=test_file.name,
                status=status,
                duration=0.0,
                error_message=error_message
            )]
            
        except Exception as e:
            self.logger.error(f"Error parsing text results: {e}")
            return []
    
    def _find_test_artifacts(self, test_id: str, artifacts_dir: Path, 
                           artifact_type: str) -> Optional[str]:
        """Find test artifacts (screenshots, videos) for a specific test"""
        try:
            if artifact_type == 'screenshot':
                search_dir = artifacts_dir / 'screenshots'
                extensions = ['.png', '.jpg', '.jpeg']
            elif artifact_type == 'video':
                search_dir = artifacts_dir / 'videos'
                extensions = ['.webm', '.mp4']
            else:
                return None
            
            if not search_dir.exists():
                return None
            
            # Search for files containing the test ID
            for file_path in search_dir.rglob('*'):
                if file_path.suffix.lower() in extensions:
                    if test_id in file_path.name or 'test' in file_path.name.lower():
                        return str(file_path)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding artifacts: {e}")
            return None
    
    def generate_execution_report(self, execution_result: TestSuiteResult) -> Path:
        """Generate comprehensive execution report"""
        try:
            report_dir = Path(execution_result.artifacts_dir)
            
            # Generate JSON report
            json_report_path = report_dir / 'execution_report.json'
            json_data = self._serialize_execution_result(execution_result)
            save_json(json_data, json_report_path)
            
            # Generate HTML report
            html_report_path = report_dir / 'execution_report.html'
            self._generate_html_report(execution_result, html_report_path)
            
            # Generate Markdown report
            md_report_path = report_dir / 'execution_report.md'
            self._generate_markdown_report(execution_result, md_report_path)
            
            self.logger.info(f"Execution reports generated in: {report_dir}")
            return html_report_path
            
        except Exception as e:
            self.logger.error(f"Error generating execution report: {e}")
            raise
    
    def _generate_html_report(self, execution_result: TestSuiteResult, output_path: Path):
        """Generate HTML execution report"""
        try:
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Execution Report - {execution_result.suite_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background-color: #e8f4f8; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric.passed {{ background-color: #d4edda; }}
        .metric.failed {{ background-color: #f8d7da; }}
        .metric.error {{ background-color: #fff3cd; }}
        .test-result {{ margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .test-result.passed {{ background-color: #d4edda; }}
        .test-result.failed {{ background-color: #f8d7da; }}
        .test-result.error {{ background-color: #fff3cd; }}
        .artifact-link {{ margin: 5px; padding: 5px 10px; background-color: #007bff; color: white; text-decoration: none; border-radius: 3px; }}
        .error-message {{ background-color: #f8f9fa; padding: 10px; border-left: 4px solid #dc3545; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Execution Report</h1>
        <p><strong>Suite:</strong> {execution_result.suite_name}</p>
        <p><strong>Execution ID:</strong> {execution_result.suite_id}</p>
        <p><strong>Start Time:</strong> {execution_result.start_time}</p>
        <p><strong>End Time:</strong> {execution_result.end_time}</p>
        <p><strong>Duration:</strong> {execution_result.total_duration:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>Total Tests</h3>
            <p>{execution_result.total_tests}</p>
        </div>
        <div class="metric passed">
            <h3>Passed</h3>
            <p>{execution_result.passed}</p>
        </div>
        <div class="metric failed">
            <h3>Failed</h3>
            <p>{execution_result.failed}</p>
        </div>
        <div class="metric error">
            <h3>Errors</h3>
            <p>{execution_result.errors}</p>
        </div>
    </div>
    
    <h2>Test Results</h2>
"""
            
            for test_result in execution_result.test_results:
                status_class = test_result.status if isinstance(test_result.status, str) else test_result.status.value
                status_str = test_result.status if isinstance(test_result.status, str) else test_result.status.value
                html_content += f"""
    <div class="test-result {status_class}">
        <h3>{test_result.test_name}</h3>
        <p><strong>Status:</strong> {status_str.upper()}</p>
        <p><strong>Duration:</strong> {test_result.duration:.2f} seconds</p>
        <p><strong>Test ID:</strong> {test_result.test_id}</p>
"""
                
                if test_result.error_message:
                    html_content += f"""
        <div class="error-message">
            <strong>Error:</strong> {test_result.error_message}
        </div>
"""
                
                # Add artifact links
                if test_result.screenshot_path:
                    html_content += f'<a href="{test_result.screenshot_path}" class="artifact-link">View Screenshot</a>'
                
                if test_result.video_path:
                    html_content += f'<a href="{test_result.video_path}" class="artifact-link">View Video</a>'
                
                html_content += '</div>'
            
            html_content += """
</body>
</html>
"""
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
        except Exception as e:
            self.logger.error(f"Error generating HTML report: {e}")
            raise
    
    def _generate_markdown_report(self, execution_result: TestSuiteResult, output_path: Path):
        """Generate Markdown execution report"""
        try:
            md_content = f"""# Test Execution Report
    ## Suite Information
    - **Suite Name**: {execution_result.suite_name}
    - **Execution ID**: {execution_result.suite_id}
    - **Start Time**: {execution_result.start_time}
    - **End Time**: {execution_result.end_time}
    - **Total Duration**: {execution_result.total_duration:.2f} seconds
    ## Summary
    - **Total Tests**: {execution_result.total_tests}
    - **Passed**: {execution_result.passed}
    - **Failed**: {execution_result.failed}
    - **Errors**: {execution_result.errors}
    - **Success Rate**: {(execution_result.passed / execution_result.total_tests * 100):.1f}%
    ## Test Results
    """
            
            for test_result in execution_result.test_results:
                # Handle both string and enum status types
                status_str = test_result.status if isinstance(test_result.status, str) else test_result.status.value
                
                status_emoji = {
                    "passed": "✅",
                    "failed": "❌", 
                    "error": "⚠️",
                    "skipped": "⏭️"
                }.get(status_str.lower(), "❓")
                
                md_content += f"""
    ### {status_emoji} {test_result.test_name}
    - **Status**: {status_str.upper()}
    - **Duration**: {test_result.duration:.2f} seconds
    - **Test ID**: {test_result.test_id}
    """
                
                if test_result.error_message:
                    md_content += f"- **Error**: {test_result.error_message}\n"
                
                if test_result.screenshot_path:
                    md_content += f"- **Screenshot**: {test_result.screenshot_path}\n"
                
                if test_result.video_path:
                    md_content += f"- **Video**: {test_result.video_path}\n"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
        except Exception as e:
            self.logger.error(f"Error generating Markdown report: {e}")
            raise
    
    def _serialize_execution_result(self, execution_result: TestSuiteResult) -> Dict[str, Any]:
        """Serialize execution result to dictionary"""
        return {
            'suite_id': execution_result.suite_id,
            'suite_name': execution_result.suite_name,
            'total_tests': execution_result.total_tests,
            'passed': execution_result.passed,
            'failed': execution_result.failed,
            'skipped': execution_result.skipped,
            'errors': execution_result.errors,
            'total_duration': execution_result.total_duration,
            'start_time': execution_result.start_time,
            'end_time': execution_result.end_time,
            'artifacts_dir': execution_result.artifacts_dir,
            'report_path': execution_result.report_path,
            'test_results': [
                {
                    'test_id': tr.test_id,
                    'test_name': tr.test_name,
                    'status': tr.status if isinstance(tr.status, str) else tr.status.value,
                    'duration': tr.duration,
                    'error_message': tr.error_message,
                    'screenshot_path': tr.screenshot_path,
                    'video_path': tr.video_path,
                    'retry_count': tr.retry_count
                }
                for tr in execution_result.test_results
            ]
        }
    
    def update_stats(self, execution_result: TestSuiteResult):
        """Update agent statistics"""
        self.stats['total_executions'] += 1
        self.stats['total_tests_run'] += execution_result.total_tests
        self.stats['total_passed'] += execution_result.passed
        self.stats['total_failed'] += execution_result.failed
        self.stats['total_errors'] += execution_result.errors
        self.stats['last_execution'] = execution_result.end_time
        
        # Add to execution history (keep last 10)
        self.stats['execution_history'].append({
            'suite_id': execution_result.suite_id,
            'timestamp': execution_result.end_time,
            'total_tests': execution_result.total_tests,
            'passed': execution_result.passed,
            'failed': execution_result.failed,
            'duration': execution_result.total_duration
        })
        
        # Keep only last 10 executions
        if len(self.stats['execution_history']) > 10:
            self.stats['execution_history'] = self.stats['execution_history'][-10:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            'agent_name': self.name,
            'stats': self.stats.copy(),
            'config': {
                'base_url': self.base_url,
                'headless': self.headless,
                'browser': self.browser,
                'timeout': self.timeout,
                'video_enabled': self.video_enabled,
                'screenshot_enabled': self.screenshot_enabled,
                'retries': self.retries
            },
            'directories': {
                'test_scripts': str(self.test_scripts_dir),
                'reports': str(self.reports_dir),
                'screenshots': str(self.screenshots_dir),
                'videos': str(self.videos_dir)
            }
        }
    
    def list_execution_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent execution reports"""
        try:
            reports = []
            
            for report_dir in sorted(self.reports_dir.iterdir(), reverse=True):
                if report_dir.is_dir() and report_dir.name.startswith('exec_'):
                    report_file = report_dir / 'execution_report.json'
                    if report_file.exists():
                        try:
                            report_data = load_json(report_file)
                            reports.append(report_data)
                            if len(reports) >= limit:
                                break
                        except Exception as e:
                            self.logger.warning(f"Error loading report {report_file}: {e}")
            
            return reports
            
        except Exception as e:
            self.logger.error(f"Error listing execution reports: {e}")
            return []

def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Execute Playwright tests')
    parser.add_argument('--test-path', type=str, help='Path to test suite or specific test file')
    parser.add_argument('--test-type', type=str, default='recruter_ai', help='Type of tests to run')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--browser', type=str, default='chromium', choices=['chromium', 'firefox', 'webkit'], help='Browser to use')
    parser.add_argument('--retries', type=int, default=2, help='Number of retries for failed tests')
    parser.add_argument('--timeout', type=int, default=30000, help='Test timeout in milliseconds')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create agent configuration
    config = {
        'headless': args.headless,
        'browser': args.browser,
        'retries': args.retries,
        'timeout': args.timeout,
        'test_type': args.test_type
    }
    
    # Create and run agent
    agent = TestExecutionAgent(config)
    
    input_data = {
        'test_suite_path': args.test_path,
        'test_type': args.test_type,
        'execution_config': config
    }
    
    result = agent.process(input_data)
    
    if result.success:
        print(f"✅ Test execution completed successfully!")
        print(f"📊 Results: {result.data.get('execution_result', {}).get('passed', 0)}/{result.data.get('execution_result', {}).get('total_tests', 0)} tests passed")
        print(f"📄 Report: {result.data.get('report_path', 'N/A')}")
    else:
        print(f"❌ Test execution failed: {result.error}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())