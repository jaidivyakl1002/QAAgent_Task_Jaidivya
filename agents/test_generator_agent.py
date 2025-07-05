import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from agents.base_agent import BaseAgent
from models.test_case import (
    AgentResponse, TestSuite, TestCase, ProcessedVideo, 
    RAGQuery, TestType, Priority
)
from core.rag_engine import RAGEngine
from core.test_case_generator import TestCaseGenerator
from core.test_scripts_generator import PlaywrightTestGenerator
from utils.file_utils import save_json, load_json
from config.settings import settings
from enum import Enum

logger = logging.getLogger(__name__)

class ProcessingMode(Enum):
    """Processing modes for the combined agent"""
    GENERATE_TEST_CASES = "generate_test_cases"
    GENERATE_SCRIPTS = "generate_scripts"
    FULL_PIPELINE = "full_pipeline"

class TestGeneratorAgent(BaseAgent):
    """Agent responsible for generating test cases from video content using RAG"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("CombinedTestAgent", config)
        
        # CRITICAL FIX: Ensure all directories exist BEFORE initializing RAG engine
        settings.ensure_directories()
        
        # Create vectorstore directory explicitly and ensure it exists
        vectorstore_dir = settings.VECTORSTORE_DIR
        vectorstore_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify the directory exists before proceeding
        if not vectorstore_dir.exists():
            raise RuntimeError(f"Failed to create vectorstore directory: {vectorstore_dir}")
        
        self.logger.info(f"Vectorstore directory created/verified: {vectorstore_dir}")
        
        # Initialize RAG engine for test case generation
        self.rag_engine = RAGEngine(
            model_name=self.get_config('embedding_model', 'all-MiniLM-L6-v2'),
            vector_store_path=self.get_config('vector_store_path', str(vectorstore_dir)),
            openai_api_key=self.get_config('openai_api_key', settings.OPENAI_API_KEY)
        )
        
        # Initialize test case generator
        self.test_case_generator = TestCaseGenerator(
            rag_engine=self.rag_engine,
            config=self.get_config('generator_config', {})
        )
        
        # Initialize Playwright test generator
        self.playwright_generator = PlaywrightTestGenerator(
            base_url=self.get_config('base_url', settings.RECRUTER_BASE_URL)
        )
        
        # Use settings for output paths
        self.test_cases_dir = settings.TEST_CASES_DIR
        self.scripts_base_dir = settings.GENERATED_TESTS_DIR
        self.reports_dir = settings.REPORTS_DIR
        self.screenshots_dir = settings.SCREENSHOTS_DIR
        self.videos_dir = settings.VIDEOS_TEST_DIR
        
        # Ensure all output directories exist
        for directory in [self.test_cases_dir, self.scripts_base_dir, self.reports_dir, 
                         self.screenshots_dir, self.videos_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Output directory ensured: {directory}")
        
        # Combined statistics
        self.stats = {
            'test_cases_generated': 0,
            'scripts_generated': 0,
            'full_pipelines_executed': 0,
            'last_run': None,
            'errors': []
        }
        
        self.logger.info("CombinedTestAgent initialized with dual functionality")
        self.logger.info(f"Test cases directory: {self.test_cases_dir}")
        self.logger.info(f"Scripts base directory: {self.scripts_base_dir}")
        self.logger.info(f"Reports directory: {self.reports_dir}")
    
    def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Main processing method that handles different modes of operation
        
        Args:
            input_data: Dict containing:
                - mode: ProcessingMode (required)
                - test_type: str (optional, defaults to 'recruter_ai')
                - For test case generation: 'processed_video' and optional 'requirements'
                - For script generation: 'test_cases' and optional 'output_dir'
                - For full pipeline: 'processed_video' and optional 'requirements'
        """
        try:
            # Validate input
            if not isinstance(input_data, dict):
                return self.create_error_response("Input must be a dictionary")
            
            mode = input_data.get('mode')
            if not mode:
                return self.create_error_response("Missing 'mode' in input data")
            
            # Convert string mode to enum if necessary
            if isinstance(mode, str):
                try:
                    mode = ProcessingMode(mode)
                except ValueError:
                    return self.create_error_response(f"Invalid mode: {mode}")
            
            # Extract test type for organization
            test_type = input_data.get('test_type', 'recruter_ai')
            
            # Route to appropriate processing method
            if mode == ProcessingMode.GENERATE_TEST_CASES:
                return self._process_test_case_generation(input_data, test_type)
            elif mode == ProcessingMode.GENERATE_SCRIPTS:
                return self._process_script_generation(input_data, test_type)
            elif mode == ProcessingMode.FULL_PIPELINE:
                return self._process_full_pipeline(input_data, test_type)
            else:
                return self.create_error_response(f"Unsupported mode: {mode}")
            
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            self.stats['errors'].append(error_msg)
            self.logger.error(error_msg)
            return self.create_error_response(error_msg)
    
    def _process_test_case_generation(self, input_data: Dict[str, Any], test_type: str = 'recruter_ai') -> AgentResponse:
        """Process video content and generate test cases"""
        try:
            # Validate input for test case generation
            if 'processed_video' not in input_data:
                return self.create_error_response("Missing 'processed_video' in input")
            
            processed_video_data = input_data['processed_video']
            
            # Convert to ProcessedVideo if it's a dict
            if isinstance(processed_video_data, dict):
                processed_video = ProcessedVideo(**processed_video_data)
            elif isinstance(processed_video_data, ProcessedVideo):
                processed_video = processed_video_data
            else:
                return self.create_error_response("Invalid processed_video format")
            
            # Add video content to RAG engine
            self.logger.info(f"Adding video content to RAG engine: {processed_video.title}")
            self.rag_engine.add_video_segments(processed_video)
            
            # Save vector store with error handling
            try:
                self.rag_engine.save_vector_store()
                self.logger.info("Vector store saved successfully")
            except Exception as save_error:
                self.logger.warning(f"Failed to save vector store: {save_error}")
                # Continue processing even if save fails
            
            # Generate test cases
            additional_requirements = input_data.get('requirements', {})
            test_suite = self.generate_test_suite(processed_video, additional_requirements, test_type)
            
            # Save test suite
            output_path = self.save_test_suite(test_suite)
            
            # Update stats
            self.stats['test_cases_generated'] += len(test_suite.test_cases)
            self.stats['last_run'] = datetime.now().isoformat()
            
            self.log_operation(
                "test_cases_generated",
                {
                    'test_suite_id': test_suite.id,
                    'test_count': len(test_suite.test_cases),
                    'test_type': test_type,
                    'output_path': str(output_path)
                }
            )
            
            return self.create_success_response(
                f"Generated {len(test_suite.test_cases)} test cases from video content for {test_type}",
                {
                    'test_suite': test_suite.dict(),
                    'output_path': str(output_path),
                    'test_type': test_type,
                    'rag_stats': self.rag_engine.get_stats(),
                    'mode': 'test_case_generation'
                }
            )
            
        except Exception as e:
            error_msg = f"Test case generation failed: {str(e)}"
            self.stats['errors'].append(error_msg)
            self.logger.error(error_msg)
            raise
    
    def _process_script_generation(self, input_data: Dict[str, Any], test_type: str = 'recruter_ai') -> AgentResponse:
        """Convert test cases into Playwright scripts"""
        try:
            # Validate input for script generation
            test_cases = input_data.get('test_cases', [])
            if not test_cases:
                return self.create_error_response("No test cases provided for script generation")
            
            # Handle different input formats for test_cases
            processed_test_cases = []
            
            for tc in test_cases:
                if isinstance(tc, TestCase):
                    # If it's already a TestCase object, convert to dict for PlaywrightTestGenerator
                    processed_test_cases.append(tc.dict())
                elif isinstance(tc, dict):
                    # If it's a dictionary, check if it needs to be converted from TestCase or is already a dict
                    if 'id' in tc and 'title' in tc and 'steps' in tc:
                        # It's already in the expected format
                        processed_test_cases.append(tc)
                    else:
                        # Try to create TestCase and then convert to dict
                        try:
                            test_case_obj = TestCase(**tc)
                            processed_test_cases.append(test_case_obj.dict())
                        except Exception as e:
                            self.logger.warning(f"Failed to convert test case dict: {e}")
                            # Use the original dict if conversion fails
                            processed_test_cases.append(tc)
                else:
                    self.logger.warning(f"Unexpected test case format: {type(tc)}")
                    continue
            
            if not processed_test_cases:
                return self.create_error_response("No valid test cases found after processing")
            
            # Get organized output directory using settings
            output_dir = input_data.get('output_dir')
            if not output_dir:
                output_dir = str(settings.get_test_output_dir(test_type))
            
            # Ensure output directory exists
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Generate Playwright scripts
            self.logger.info(f"Generating Playwright scripts for {len(processed_test_cases)} test cases (type: {test_type})")
            result = self.playwright_generator.generate_test_suite(processed_test_cases, output_dir)
            
            if 'error' in result:
                return self.create_error_response(f"Script generation failed: {result['error']}")
            
            # Update stats
            self.stats['scripts_generated'] += result['stats']['successful']
            self.stats['last_run'] = datetime.now().isoformat()
            
            self.log_operation(
                "scripts_generated",
                {
                    'scripts_count': result['stats']['successful'],
                    'test_type': test_type,
                    'output_dir': output_dir
                }
            )
            
            return self.create_success_response(
                f"Generated {result['stats']['successful']} Playwright test scripts for {test_type}",
                {
                    'generation_result': result,
                    'output_dir': output_dir,
                    'test_type': test_type,
                    'mode': 'script_generation'
                }
            )
            
        except Exception as e:
            error_msg = f"Script generation failed: {str(e)}"
            self.stats['errors'].append(error_msg)
            self.logger.error(error_msg)
            raise
    
    def _process_full_pipeline(self, input_data: Dict[str, Any], test_type: str = 'recruter_ai') -> AgentResponse:
        """Execute the full pipeline: video -> test cases -> scripts"""
        try:
            self.logger.info(f"Starting full pipeline execution for test type: {test_type}")
            
            # Step 1: Generate test cases from video
            self.logger.info("Step 1: Generating test cases from video")
            test_case_response = self._process_test_case_generation(input_data, test_type)
            
            if not test_case_response.success:
                return test_case_response
            
            # Extract test suite from response
            test_suite_data = test_case_response.data.get('test_suite')
            if not test_suite_data:
                return self.create_error_response("Failed to extract test suite from generation step")
            
            test_suite = TestSuite(**test_suite_data)
            
            # Step 2: Generate scripts from test cases
            self.logger.info("Step 2: Generating Playwright scripts from test cases")
            script_input = {
                'test_cases': test_suite.test_cases,  # Pass TestCase objects directly
                'output_dir': input_data.get('output_dir')  # Let the method use settings if not provided
            }
            
            script_response = self._process_script_generation(script_input, test_type)
            
            if not script_response.success:
                return script_response
            
            # Update stats
            self.stats['full_pipelines_executed'] += 1
            self.stats['last_run'] = datetime.now().isoformat()
            
            self.log_operation(
                "full_pipeline_executed",
                {
                    'test_suite_id': test_suite.id,
                    'test_cases_count': len(test_suite.test_cases),
                    'scripts_count': script_response.data['generation_result']['stats']['successful'],
                    'test_type': test_type
                }
            )
            
            return self.create_success_response(
                f"Full pipeline completed for {test_type}: {len(test_suite.test_cases)} test cases -> {script_response.data['generation_result']['stats']['successful']} scripts",
                {
                    'test_suite': test_suite.dict(),
                    'test_cases_output': test_case_response.data['output_path'],
                    'scripts_output': script_response.data['output_dir'],
                    'generation_result': script_response.data['generation_result'],
                    'test_type': test_type,
                    'mode': 'full_pipeline'
                }
            )
            
        except Exception as e:
            error_msg = f"Full pipeline execution failed: {str(e)}"
            self.stats['errors'].append(error_msg)
            self.logger.error(error_msg)
            raise
    
    # Test case generation methods (from original TestGeneratorAgent)
    def generate_test_suite(self, processed_video: ProcessedVideo, 
                           requirements: Dict[str, Any] = None, 
                           test_type: str = 'recruter_ai') -> TestSuite:
        """Generate a comprehensive test suite from processed video"""
        try:
            # Create test suite with test type in ID
            test_suite = TestSuite(
                id=f"ts_{test_type}_{processed_video.title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                name=f"Test Suite for {processed_video.title} ({test_type})",
                description=f"Automated test suite generated from video: {processed_video.title} (Test Type: {test_type})",
                source_video=processed_video.url,
                created_at=datetime.now().isoformat()
            )
            
            # Generate different types of test cases
            test_cases = []
            
            # 1. Functional test cases from user flows
            functional_tests = self.test_case_generator.generate_functional_tests(
                processed_video, requirements
            )
            test_cases.extend(functional_tests)
            
            # 2. Edge case tests
            edge_case_tests = self.test_case_generator.generate_edge_case_tests(
                processed_video, requirements
            )
            test_cases.extend(edge_case_tests)
            
            # 3. Cross-browser tests
            cross_browser_tests = self.test_case_generator.generate_cross_browser_tests(
                processed_video, requirements
            )
            test_cases.extend(cross_browser_tests)
            
            # 4. Accessibility tests
            accessibility_tests = self.test_case_generator.generate_accessibility_tests(
                processed_video, requirements
            )
            test_cases.extend(accessibility_tests)
            
            # 5. Performance tests
            performance_tests = self.test_case_generator.generate_performance_tests(
                processed_video, requirements
            )
            test_cases.extend(performance_tests)
            
            test_suite.test_cases = test_cases
            
            self.logger.info(f"Generated {len(test_cases)} test cases for video: {processed_video.title} (type: {test_type})")
            
            return test_suite
            
        except Exception as e:
            self.logger.error(f"Error generating test suite: {e}")
            raise
    
    def save_test_suite(self, test_suite: TestSuite) -> Path:
        """Save test suite to different formats"""
        try:
            # Use settings directory structure
            base_path = self.test_cases_dir / test_suite.id
            base_path.mkdir(parents=True, exist_ok=True)
            
            # Save as JSON
            json_path = base_path / f"{test_suite.id}.json"
            save_json(test_suite.model_dump(), json_path)
            
            # Save as Markdown for human readability
            markdown_path = base_path / f"{test_suite.id}.md"
            self.save_test_suite_markdown(test_suite, markdown_path)
            
            # Save individual test cases
            for test_case in test_suite.test_cases:
                test_case_path = base_path / f"{test_case.id}.json"
                save_json(test_case.model_dump(), test_case_path)
            
            self.logger.info(f"Test suite saved to: {json_path}")
            return json_path
            
        except Exception as e:
            self.logger.error(f"Error saving test suite: {e}")
            raise
    
    def save_test_suite_markdown(self, test_suite: TestSuite, output_path: Path):
        """Save test suite as markdown for human readability"""
        try:
            md_content = f"""# {test_suite.name}

## Description
{test_suite.description}

## Test Suite Information
- **ID**: {test_suite.id}
- **Created**: {test_suite.created_at}
- **Source Video**: {test_suite.source_video}
- **Total Test Cases**: {len(test_suite.test_cases)}

## Test Cases Summary
"""
            
            # Group test cases by type
            test_by_type = {}
            for test_case in test_suite.test_cases:
                test_type = test_case.test_type
                if test_type not in test_by_type:
                    test_by_type[test_type] = []
                test_by_type[test_type].append(test_case)
            
            for test_type, tests in test_by_type.items():
                md_content += f"\n### {test_type.title()} Tests ({len(tests)})\n"
                for test in tests:
                    md_content += f"- **{test.title}** (Priority: {test.priority})\n"
            
            md_content += "\n## Detailed Test Cases\n"
            
            for i, test_case in enumerate(test_suite.test_cases, 1):
                md_content += f"""
### {i}. {test_case.title}

**ID**: {test_case.id}  
**Type**: {test_case.test_type}  
**Priority**: {test_case.priority}  
**Estimated Duration**: {test_case.estimated_duration or 'N/A'} seconds

**Description**: {test_case.description}

**Preconditions**:
"""
                for precondition in test_case.preconditions:
                    md_content += f"- {precondition}\n"
                
                md_content += "\n**Test Steps**:\n"
                for j, step in enumerate(test_case.steps, 1):
                    md_content += f"{j}. **{step.action}**\n"
                    md_content += f"   - Selector: `{step.selector}`\n"
                    if step.value:
                        md_content += f"   - Value: `{step.value}`\n"
                    if step.expected_result:
                        md_content += f"   - Expected: {step.expected_result}\n"
                
                md_content += "\n**Expected Results**:\n"
                for result in test_case.expected_results:
                    md_content += f"- {result}\n"
                
                if test_case.tags:
                    md_content += f"\n**Tags**: {', '.join(test_case.tags)}\n"
                
                md_content += "\n---\n"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            self.logger.info(f"Test suite markdown saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving markdown: {e}")
            raise
    
    # Utility methods
    def query_test_knowledge(self, query: str, top_k: int = 5) -> AgentResponse:
        """Query the RAG engine for test-related knowledge"""
        try:
            rag_query = RAGQuery(
                query=query,
                top_k=top_k,
                similarity_threshold=0.7
            )
            
            result = self.rag_engine.query(rag_query)
            
            return self.create_success_response(
                f"Retrieved {len(result.results)} relevant documents",
                {
                    'query': query,
                    'results': result.results,
                    'generated_response': result.generated_response,
                    'confidence': result.confidence
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error querying knowledge: {e}")
            return self.create_error_response(f"Knowledge query failed: {str(e)}")
    
    def load_test_suite(self, test_suite_id: str) -> Optional[TestSuite]:
        """Load a previously generated test suite"""
        try:
            json_path = self.test_cases_dir / test_suite_id / f"{test_suite_id}.json"
            if json_path.exists():
                data = load_json(json_path)
                return TestSuite(**data)
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading test suite: {e}")
            return None
    
    def list_test_suites(self, test_type: str = None) -> List[Dict[str, Any]]:
        """List all generated test suites, optionally filtered by test type"""
        try:
            suites = []
            for suite_dir in self.test_cases_dir.iterdir():
                if suite_dir.is_dir():
                    json_file = suite_dir / f"{suite_dir.name}.json"
                    if json_file.exists():
                        try:
                            data = load_json(json_file)
                            suite_info = {
                                'id': data.get('id'),
                                'name': data.get('name'),
                                'created_at': data.get('created_at'),
                                'test_count': len(data.get('test_cases', [])),
                                'source_video': data.get('source_video'),
                                'test_type': self._extract_test_type_from_id(data.get('id', ''))
                            }
                            
                            # Filter by test type if specified
                            if test_type is None or suite_info['test_type'] == test_type:
                                suites.append(suite_info)
                                
                        except Exception as e:
                            self.logger.warning(f"Error loading suite {suite_dir.name}: {e}")
                            continue
            
            return sorted(suites, key=lambda x: x.get('created_at', ''), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error listing test suites: {e}")
            return []
    
    def _extract_test_type_from_id(self, test_suite_id: str) -> str:
        """Extract test type from test suite ID"""
        try:
            # Expected format: ts_{test_type}_{video_title}_{timestamp}
            parts = test_suite_id.split('_')
            if len(parts) >= 3 and parts[0] == 'ts':
                return parts[1]
            return 'unknown'
        except Exception:
            return 'unknown'
    
    def get_directory_structure(self) -> Dict[str, Any]:
        """Get current directory structure for debugging"""
        try:
            return {
                'test_cases_dir': str(self.test_cases_dir),
                'scripts_base_dir': str(self.scripts_base_dir),
                'reports_dir': str(self.reports_dir),
                'screenshots_dir': str(self.screenshots_dir),
                'videos_dir': str(self.videos_dir),
                'vectorstore_dir': str(settings.VECTORSTORE_DIR),
                'organized_output_dirs': {
                    'recruter_ai': str(settings.get_test_output_dir('recruter_ai')),
                    'custom': str(settings.get_test_output_dir('custom')),
                },
                'reports_dirs': {
                    'general': str(settings.get_reports_dir()),
                    'recruter_ai': str(settings.get_reports_dir('recruter_ai')),
                    'custom': str(settings.get_reports_dir('custom')),
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting directory structure: {e}")
            return {'error': str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics"""
        try:
            suites = self.list_test_suites()
            
            # Get RAG stats
            rag_stats = {}
            try:
                rag_stats = self.rag_engine.get_stats()
            except Exception as e:
                self.logger.warning(f"Could not get RAG stats: {e}")
            
            # Get Playwright generator stats
            playwright_stats = {}
            try:
                playwright_stats = self.playwright_generator.get_stats() if hasattr(self.playwright_generator, 'get_stats') else {}
            except Exception as e:
                self.logger.warning(f"Could not get Playwright stats: {e}")
            
            # Group suites by test type
            suites_by_type = {}
            for suite in suites:
                test_type = suite.get('test_type', 'unknown')
                if test_type not in suites_by_type:
                    suites_by_type[test_type] = []
                suites_by_type[test_type].append(suite)
            
            return {
                'agent_name': self.name,
                'combined_stats': self.stats.copy(),
                'test_suites': {
                    'total': len(suites),
                    'by_type': {k: len(v) for k, v in suites_by_type.items()},
                    'recent': suites[:5]
                },
                'directory_structure': self.get_directory_structure(),
                'rag_stats': rag_stats,
                'playwright_stats': playwright_stats,
                'capabilities': [
                    'test_case_generation',
                    'script_generation', 
                    'full_pipeline',
                    'knowledge_query',
                    'test_type_organization'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {
                'agent_name': self.name,
                'error': str(e)
            }