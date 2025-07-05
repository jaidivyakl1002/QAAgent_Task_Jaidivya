import os
import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Import your existing components
from core.video_processor import VideoProcessor
from agents.test_generator_agent import TestGeneratorAgent
from models.test_case import ProcessedVideo, VideoSegment, AgentResponse
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QAAgentPipeline:
    """Main pipeline that orchestrates video processing and test case generation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.video_processor = VideoProcessor()
        self.test_generator_agent = TestGeneratorAgent(config)
        
        # Setup directories using the updated settings
        self.setup_directories()
        
        logger.info("QA Agent Pipeline initialized")
    
    def setup_directories(self):
        """Create necessary directories using settings"""
        try:
            settings.ensure_directories()
            
            # Ensure vectorstore directory exists (fix for FAISS error)
            vectorstore_dir = Path(settings.DATA_DIR) / 'vectorstore'
            vectorstore_dir.mkdir(parents=True, exist_ok=True)
            
            # Ensure all other critical directories exist
            critical_dirs = [
                settings.VIDEOS_DIR,
                settings.TRANSCRIPTS_DIR,
                settings.SCREENSHOTS_DIR,
                settings.VIDEOS_TEST_DIR,
                settings.get_test_output_dir('recruter_ai'),
                settings.get_reports_dir('recruter_ai'),
                settings.get_test_output_dir('custom'),
                settings.get_reports_dir('custom')
            ]
            
            for dir_path in critical_dirs:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
            
            logger.info("All directories created successfully")
            
        except Exception as e:
            logger.error(f"Error setting up directories: {e}")
            raise
    
    def process_recruter_video(self) -> AgentResponse:
        """
        Complete pipeline for processing Recruter.ai video:
        1. Download video
        2. Transcribe
        3. Process transcript into segments
        4. Generate test cases
        """
        try:
            logger.info("Starting Recruter.ai video processing pipeline")
            
            # Step 1: Download and transcribe video
            logger.info("Step 1: Downloading and transcribing video...")
            transcript_data = self.video_processor.process_recruter_video()
            
            if not transcript_data:
                return AgentResponse(
                    success=False,
                    message="Failed to download or transcribe video",
                    error="Video processing failed"
                )
            
            # Step 2: Process transcript into structured format
            logger.info("Step 2: Processing transcript into structured format...")
            processed_video = self.create_processed_video(transcript_data)
            
            # Step 3: Generate test cases using the agent
            logger.info("Step 3: Generating test cases...")
            test_generation_input = {
                'processed_video': processed_video,
                'requirements': self.get_default_requirements()
            }
            
            agent_response = self.test_generator_agent.process(test_generation_input)
            
            if agent_response.success:
                logger.info(f"Pipeline completed successfully! {agent_response.message}")
                
                # Add pipeline metadata
                agent_response.data['pipeline_info'] = {
                    'video_url': "https://youtu.be/IK62Rk47aas",
                    'processing_time': datetime.now().isoformat(),
                    'transcript_segments': len(transcript_data.get('segments', [])),
                    'video_duration': processed_video.duration
                }
                
                return agent_response
            else:
                return agent_response
                
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return AgentResponse(
                success=False,
                message=f"Pipeline failed: {str(e)}",
                error=str(e)
            )
    
    def create_processed_video(self, transcript_data: Dict[str, Any]) -> ProcessedVideo:
        """Convert raw transcript data into ProcessedVideo model"""
        try:
            # Extract video info
            video_url = "https://youtu.be/IK62Rk47aas"
            video_title = "Recruter.ai How-to Tutorial"
            
            # Get duration from segments
            segments = transcript_data.get('segments', [])
            duration = segments[-1]['end'] if segments else 0
            
            # Create video segments
            video_segments = []
            ui_components = set()
            extracted_flows = []
            
            for segment in segments:
                # Extract UI elements and flows from transcript
                transcript_text = segment['text'].lower()
                
                # Common UI elements to look for
                ui_keywords = [
                    'button', 'click', 'input', 'field', 'form', 'dropdown', 
                    'menu', 'link', 'tab', 'page', 'screen', 'dialog', 
                    'popup', 'notification', 'login', 'signup', 'dashboard',
                    'profile', 'settings', 'search', 'upload', 'download'
                ]
                
                found_ui_elements = []
                for keyword in ui_keywords:
                    if keyword in transcript_text:
                        found_ui_elements.append(keyword)
                        ui_components.add(keyword)
                
                # Extract potential user flows
                flow_keywords = [
                    'sign up', 'log in', 'create account', 'fill form',
                    'submit', 'upload', 'download', 'navigate', 'search',
                    'filter', 'sort', 'select', 'choose', 'configure'
                ]
                
                for flow in flow_keywords:
                    if flow in transcript_text:
                        extracted_flows.append(f"User can {flow}")
                
                # Create video segment
                video_segment = VideoSegment(
                    start_time=segment['start'],
                    end_time=segment['end'],
                    transcript=segment['text'],
                    action_description=self.extract_action_description(segment['text']),
                    ui_elements=found_ui_elements
                )
                video_segments.append(video_segment)
            
            # Create ProcessedVideo
            processed_video = ProcessedVideo(
                url=video_url,
                title=video_title,
                duration=duration,
                full_transcript=transcript_data.get('text', ''),
                segments=video_segments,
                extracted_flows=list(set(extracted_flows)),
                ui_components=list(ui_components)
            )
            
            # Save processed video for reference
            self.save_processed_video(processed_video)
            
            return processed_video
            
        except Exception as e:
            logger.error(f"Error creating processed video: {e}")
            raise
    
    def extract_action_description(self, transcript_text: str) -> str:
        """Extract actionable description from transcript text"""
        # Simple heuristic to identify actions
        action_verbs = [
            'click', 'tap', 'select', 'choose', 'enter', 'type', 'fill',
            'submit', 'upload', 'download', 'navigate', 'go to', 'open',
            'close', 'save', 'delete', 'edit', 'update', 'create', 'add'
        ]
        
        text_lower = transcript_text.lower()
        for verb in action_verbs:
            if verb in text_lower:
                # Extract sentence containing the action
                sentences = transcript_text.split('.')
                for sentence in sentences:
                    if verb in sentence.lower():
                        return sentence.strip()
        
        return transcript_text[:100] + "..." if len(transcript_text) > 100 else transcript_text
    
    def get_default_requirements(self) -> Dict[str, Any]:
        """Get default test requirements for Recruter.ai"""
        return {
            'target_application': 'Recruter.ai',
            'base_url': settings.RECRUTER_BASE_URL,
            'test_environments': ['chrome', 'firefox', 'safari'],
            'viewport_sizes': [
                {'width': 1920, 'height': 1080},  # Desktop
                {'width': 1366, 'height': 768},   # Laptop
                {'width': 768, 'height': 1024},   # Tablet
                {'width': 375, 'height': 667}     # Mobile
            ],
            'focus_areas': [
                'user_registration',
                'login_flow',
                'profile_creation',
                'job_posting',
                'candidate_search',
                'application_process'
            ],
            'accessibility_standards': ['WCAG 2.1 AA'],
            'performance_thresholds': {
                'page_load_time': 3000,  # 3 seconds
                'interaction_response': 200  # 200ms
            },
            'priority_flows': [
                'New user signup',
                'Login process',
                'Core functionality'
            ],
            'output_directories': {
                'tests': str(settings.get_test_output_dir('recruter_ai')),
                'reports': str(settings.get_reports_dir('recruter_ai'))
            }
        }
    
    def save_processed_video(self, processed_video: ProcessedVideo):
        """Save processed video data for reference"""
        try:
            output_path = settings.TRANSCRIPTS_DIR / "processed_recruter_video.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(processed_video.model_dump(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Processed video saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving processed video: {e}")
    
    def run_custom_video(self, video_url: str, requirements: Dict[str, Any] = None) -> AgentResponse:
        """Process a custom video URL"""
        try:
            logger.info(f"Processing custom video: {video_url}")
            
            # Download and transcribe
            audio_path = self.video_processor.download_youtube_video(
                video_url, 
                settings.VIDEOS_DIR
            )
            
            if not audio_path:
                return AgentResponse(
                    success=False,
                    message="Failed to download video",
                    error="Video download failed"
                )
            
            transcript_data = self.video_processor.transcribe_video(audio_path)
            
            if not transcript_data:
                return AgentResponse(
                    success=False,
                    message="Failed to transcribe video",
                    error="Video transcription failed"
                )
            
            # Process into structured format
            processed_video = self.create_processed_video_from_url(video_url, transcript_data)
            
            # Generate test cases with custom output directory
            if not requirements:
                requirements = self.get_default_requirements()
                requirements['output_directories'] = {
                    'tests': str(settings.get_test_output_dir('custom')),
                    'reports': str(settings.get_reports_dir('custom'))
                }
            
            test_generation_input = {
                'processed_video': processed_video,
                'requirements': requirements
            }
            
            return self.test_generator_agent.process(test_generation_input)
            
        except Exception as e:
            logger.error(f"Custom video processing error: {e}")
            return AgentResponse(
                success=False,
                message=f"Custom video processing failed: {str(e)}",
                error=str(e)
            )
    
    def create_processed_video_from_url(self, url: str, transcript_data: Dict) -> ProcessedVideo:
        """Create ProcessedVideo from custom URL"""
        # Similar to create_processed_video but with custom URL
        segments = transcript_data.get('segments', [])
        duration = segments[-1]['end'] if segments else 0
        
        # Extract title from URL or use generic
        title = f"Custom Video - {url}"
        
        video_segments = []
        for segment in segments:
            video_segment = VideoSegment(
                start_time=segment['start'],
                end_time=segment['end'],
                transcript=segment['text'],
                action_description=self.extract_action_description(segment['text']),
                ui_elements=[]
            )
            video_segments.append(video_segment)
        
        return ProcessedVideo(
            url=url,
            title=title,
            duration=duration,
            full_transcript=transcript_data.get('text', ''),
            segments=video_segments,
            extracted_flows=[],
            ui_components=[]
        )
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return {
            'agent_stats': self.test_generator_agent.get_stats(),
            'pipeline_info': {
                'video_processor': 'Whisper base model',
                'test_generator': 'RAG + LLM',
                'supported_formats': ['YouTube URLs', 'Local video files']
            }
        }
    
    def process_recruter_video_complete(self) -> Dict[str, Any]:
        """
        Complete pipeline:
        1. Process video and generate test cases
        2. Convert test cases to Playwright scripts
        3. Prepare for execution
        """
        try:
            logger.info("Starting complete Recruter.ai pipeline...")
            
            # Step 1: Process video and generate test cases and scripts
            logger.info("Step 1: Running full pipeline (video -> test cases -> scripts)...")
            transcript_data = self.video_processor.process_recruter_video()
            
            if not transcript_data:
                return {
                    'success': False,
                    'message': 'Failed to download or transcribe video',
                    'error': 'Video processing failed'
                }
            
            # Step 2: Process transcript into structured format
            logger.info("Step 2: Processing transcript into structured format...")
            processed_video = self.create_processed_video(transcript_data)
            
            # Step 3: Run full pipeline using TestGeneratorAgent
            logger.info("Step 3: Generating test cases and Playwright scripts...")
            test_generation_input = {
                'mode': 'full_pipeline',
                'processed_video': processed_video,
                'requirements': self.get_default_requirements(),
                'test_type': 'recruter_ai',
                'output_dir': str(settings.get_test_output_dir('recruter_ai'))
            }
            
            result = self.test_generator_agent.process(test_generation_input)
            
            if not result.success:
                return {
                    'success': False,
                    'message': 'Full pipeline execution failed',
                    'error': result.error
                }
            
            # Step 4: Create execution summary
            logger.info("Step 4: Creating execution summary...")
            execution_summary = self.create_execution_summary(
                result.data,
                result.data.get('generation_result', {})
            )
            
            return {
                'success': True,
                'message': 'Complete pipeline finished successfully',
                'data': {
                    'test_generation': result.data,
                    'script_generation': result.data.get('generation_result', {}),
                    'execution_summary': execution_summary,
                    'next_steps': self.get_next_steps(result.data)
                }
            }
            
        except Exception as e:
            logger.error(f"Complete pipeline error: {e}")
            return {
                'success': False,
                'message': f'Complete pipeline failed: {str(e)}',
                'error': str(e)
            }
    
    def create_execution_summary(self, test_data: Dict, script_data: Dict) -> Dict[str, Any]:
        """Create summary of what was generated"""
        test_suite = test_data.get('test_suite', {})
        stats = script_data.get('stats', {})
        
        # Count tests by type
        test_breakdown = {}
        for test_case in test_suite.get('test_cases', []):
            test_type = test_case.get('test_type', 'functional')
            test_breakdown[test_type] = test_breakdown.get(test_type, 0) + 1
        
        return {
            'timestamp': datetime.now().isoformat(),
            'video_info': {
                'url': test_data.get('pipeline_info', {}).get('video_url', 'Unknown'),
                'duration': test_data.get('pipeline_info', {}).get('video_duration', 0),
                'segments': test_data.get('pipeline_info', {}).get('transcript_segments', 0)
            },
            'test_generation': {
                'total_tests': len(test_suite.get('test_cases', [])),
                'test_breakdown': test_breakdown,
                'output_path': test_data.get('output_path', 'Unknown')
            },
            'script_generation': {
                'successful_conversions': stats.get('successful', 0),
                'failed_conversions': stats.get('failed', 0),
                'output_directory': script_data.get('output_directory', 'Unknown'),
                'generated_files': len(script_data.get('generated_files', []))
            },
            'directory_structure': {
                'tests_dir': str(settings.get_test_output_dir('recruter_ai')),
                'reports_dir': str(settings.get_reports_dir('recruter_ai')),
                'screenshots_dir': str(settings.SCREENSHOTS_DIR),
                'videos_dir': str(settings.VIDEOS_TEST_DIR)
            }
        }
    
    def get_next_steps(self, script_data: Dict) -> List[str]:
        """Provide next steps for test execution"""
        output_dir = script_data.get('output_directory', str(settings.get_test_output_dir('recruter_ai')))
        
        return [
            f"1. Navigate to the Playwright base directory: cd {settings.PLAYWRIGHT_BASE_DIR}",
            "2. Install dependencies: npm install",
            "3. Install Playwright browsers: npx playwright install",
            f"4. Run tests: npx playwright test --reporter=html --output-dir={settings.get_reports_dir('recruter_ai')}",
            f"5. Run tests with UI: npx playwright test --ui",
            f"6. View test report: npx playwright show-report {settings.get_reports_dir('recruter_ai')}",
            f"7. Debug specific test: npx playwright test --debug {output_dir}/<test-file>",
            "",
            "Generated files structure:",
            f"📁 Tests: {output_dir}",
            f"📁 Reports: {settings.get_reports_dir('recruter_ai')}",
            f"📁 Screenshots: {settings.SCREENSHOTS_DIR}",
            f"📁 Videos: {settings.VIDEOS_TEST_DIR}"
        ]
    
    def load_existing_test_cases(self, test_cases_path: str) -> List[Dict]:
        """Load test cases from JSON files"""
        try:
            test_cases = []
            test_path = Path(test_cases_path)
            
            if test_path.is_file():
                # Single file
                with open(test_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        test_cases.extend(data)
                    else:
                        test_cases.append(data)
            
            elif test_path.is_dir():
                # Directory of JSON files
                for json_file in test_path.glob('*.json'):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                test_cases.extend(data)
                            else:
                                test_cases.append(data)
                    except Exception as e:
                        logger.warning(f"Failed to load {json_file}: {e}")
            
            logger.info(f"Loaded {len(test_cases)} test cases")
            return test_cases
            
        except Exception as e:
            logger.error(f"Error loading test cases: {e}")
            return []
    
    def generate_scripts_from_existing_tests(self, test_cases_path: str, output_dir: str = None, test_type: str = "custom") -> Dict[str, Any]:
        """Generate Playwright scripts from existing test case files"""
        try:
            # Load test cases
            test_cases = self.load_existing_test_cases(test_cases_path)
            
            if not test_cases:
                return {
                    'success': False,
                    'message': 'No test cases found to convert',
                    'error': 'Empty test cases list'
                }
            
            # Use proper output directory
            if not output_dir:
                output_dir = str(settings.get_test_output_dir(test_type))
            
            # Generate scripts using TestGeneratorAgent
            script_generation_input = {
                'mode': 'generate_scripts',
                'test_cases': test_cases,
                'output_dir': output_dir,
                'test_type': test_type
            }
            
            result = self.test_generator_agent.process(script_generation_input)
            
            if result.success:
                result.data['next_steps'] = self.get_next_steps(result.data)
                result.data['directory_info'] = {
                    'tests_dir': output_dir,
                    'reports_dir': str(settings.get_reports_dir(test_type)),
                    'screenshots_dir': str(settings.SCREENSHOTS_DIR),
                    'videos_dir': str(settings.VIDEOS_TEST_DIR)
                }
            
            return {
                'success': result.success,
                'message': result.message,
                'data': result.data,
                'error': result.error
            }
            
        except Exception as e:
            logger.error(f"Error generating scripts from existing tests: {e}")
            return {
                'success': False,
                'message': f'Script generation failed: {str(e)}',
                'error': str(e)
            }

def main_enhanced():
    """Enhanced main function with script generation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='QA Agent Pipeline with Playwright Script Generation')
    parser.add_argument('--mode', choices=['full', 'generate-only', 'scripts-only'], 
                       default='full', help='Pipeline mode')
    parser.add_argument('--test-cases', type=str, help='Path to existing test cases (for scripts-only mode)')
    parser.add_argument('--output-dir', type=str, help='Output directory for generated scripts')
    parser.add_argument('--test-type', type=str, default='custom', help='Test type for organizing output')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = QAAgentPipeline()
    
    if args.mode == 'full':
        # Full pipeline: video -> test cases -> scripts
        logger.info("Running full pipeline...")
        result = pipeline.process_recruter_video_complete()
        
    elif args.mode == 'generate-only':
        # Only generate test cases
        logger.info("Generating test cases only...")
        result = pipeline.process_recruter_video()
        
        # Convert AgentResponse to dict for consistency
        if hasattr(result, 'success'):
            result = {
                'success': result.success,
                'message': result.message,
                'data': result.data,
                'error': result.error
            }
        
    elif args.mode == 'scripts-only':
        # Only generate scripts from existing test cases
        if not args.test_cases:
            logger.error("--test-cases path required for scripts-only mode")
            return {
                'success': False,
                'message': "--test-cases path required for scripts-only mode",
                'error': "Missing required argument"
            }
        
        logger.info(f"Generating scripts from: {args.test_cases}")
        result = pipeline.generate_scripts_from_existing_tests(
            args.test_cases, 
            args.output_dir,
            args.test_type
        )
    
    # Display results
    if isinstance(result, dict) and result.get('success'):
        logger.info("✅ Pipeline completed successfully!")
        
        if args.mode == 'full':
            data = result.get('data', {})
            print("\n" + "="*60)
            print("COMPLETE PIPELINE RESULTS")
            print("="*60)
            
            # Test generation summary
            test_gen = data.get('test_generation', {})
            test_suite = test_gen.get('test_suite', {})
            
            print(f"🎥 Video: {data.get('execution_summary', {}).get('video_info', {}).get('url', 'Unknown')}")
            print(f"📊 Test Cases Generated: {len(test_suite.get('test_cases', []))}")
            
            # Script generation summary
            script_gen = data.get('script_generation', {})
            stats = script_gen.get('stats', {})
            
            print(f"🎭 Playwright Scripts: {stats.get('successful', 0)} successful, {stats.get('failed', 0)} failed")
            print(f"📁 Output Directory: {script_gen.get('output_dir', 'Unknown')}")
            
            # Directory structure
            dir_structure = data.get('execution_summary', {}).get('directory_structure', {})
            if dir_structure:
                print(f"📁 Tests: {dir_structure.get('tests_dir', 'Unknown')}")
                print(f"📁 Reports: {dir_structure.get('reports_dir', 'Unknown')}")
                print(f"📁 Screenshots: {dir_structure.get('screenshots_dir', 'Unknown')}")
                print(f"📁 Videos: {dir_structure.get('videos_dir', 'Unknown')}")
            
            # Next steps
            next_steps = data.get('next_steps', [])
            if next_steps:
                print("\n📋 NEXT STEPS:")
                for step in next_steps:
                    print(f"   {step}")
                    
        elif args.mode == 'generate-only':
            # Handle test generation only
            data = result.get('data', {})
            test_suite = data.get('test_suite', {})
            
            print("\n" + "="*60)
            print("TEST GENERATION RESULTS")
            print("="*60)
            print(f"📊 Test Cases Generated: {len(test_suite.get('test_cases', []))}")
            print(f"📁 Output File: {data.get('output_path', 'Unknown')}")
            
            # Show test breakdown
            test_breakdown = {}
            for test_case in test_suite.get('test_cases', []):
                test_type = test_case.get('test_type', 'functional')
                test_breakdown[test_type] = test_breakdown.get(test_type, 0) + 1
            
            if test_breakdown:
                print("\n📈 Test Breakdown:")
                for test_type, count in test_breakdown.items():
                    print(f"   {test_type}: {count}")
                    
        elif args.mode == 'scripts-only':
            # Handle script generation only
            data = result.get('data', {})
            stats = data.get('stats', {})
            
            print("\n" + "="*60)
            print("SCRIPT GENERATION RESULTS")
            print("="*60)
            print(f"🎭 Playwright Scripts: {stats.get('successful', 0)} successful, {stats.get('failed', 0)} failed")
            print(f"📁 Output Directory: {data.get('output_dir', 'Unknown')}")
            
            # Show generated files
            generated_files = data.get('generated_files', [])
            if generated_files:
                print(f"\n📄 Generated Files ({len(generated_files)}):")
                for file in generated_files[:10]:  # Show first 10
                    print(f"   - {file}")
                if len(generated_files) > 10:
                    print(f"   ... and {len(generated_files) - 10} more")
                
            # Next steps
            next_steps = data.get('next_steps', [])
            if next_steps:
                print("\n📋 NEXT STEPS:")
                for step in next_steps:
                    print(f"   {step}")
                    
    else:
        # Handle failures
        error_msg = result.get('message', 'Unknown error') if isinstance(result, dict) else str(result)
        logger.error(f"❌ Pipeline failed: {error_msg}")
        
        # Show error details if available
        if isinstance(result, dict) and result.get('error'):
            logger.error(f"   Error details: {result['error']}")
    
    return result


if __name__ == "__main__":
    # Run the pipeline
    result = main_enhanced()
    
    # Exit with appropriate code - Fixed AttributeError
    success = result.get('success', False) if isinstance(result, dict) else False
    exit(0 if success else 1)