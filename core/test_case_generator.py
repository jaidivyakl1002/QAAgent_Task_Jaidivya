import logging
from typing import Dict, Any, List, Optional
from uuid import uuid4
from datetime import datetime
from models.test_case import TestCase, TestStep, TestType, Priority, ProcessedVideo, RAGQuery
from core.rag_engine import RAGEngine

logger = logging.getLogger(__name__)

class TestCaseGenerator:
    """Class responsible for generating various types of test cases from video content"""
    
    def __init__(self, rag_engine: RAGEngine, config: Dict[str, Any] = None):
        """
        Initialize TestCaseGenerator with RAG engine
        
        Args:
            rag_engine: RAGEngine instance for querying video content
            config: Configuration dictionary
        """
        self.rag_engine = rag_engine
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuration with defaults
        self.max_test_cases_per_type = self.config.get('max_test_cases_per_type', 10)
        self.default_timeout = self.config.get('default_timeout', 30)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.7)
        
    def _generate_test_id(self, prefix: str) -> str:
        """Generate unique test case ID"""
        return f"{prefix}_{uuid4().hex[:8]}"
    
    def _create_test_step(self, action: str, selector: str, value: Optional[str] = None,
                         expected_result: Optional[str] = None, wait_condition: Optional[str] = None,
                         screenshot: bool = False) -> TestStep:
        """Create a test step with provided parameters"""
        return TestStep(
            action=action,
            selector=selector,
            value=value,
            expected_result=expected_result,
            wait_condition=wait_condition,
            screenshot=screenshot
        )

    def _extract_ui_elements_from_segment(self, segment_metadata: Dict[str, Any]) -> List[str]:
        """Extract UI elements from segment metadata safely"""
        ui_elements = segment_metadata.get('ui_elements', [])
        if not ui_elements:
            return ['.main-element']  # Default fallback
        return [f".{element}" for element in ui_elements if element]

    def _create_selector_from_ui_elements(self, ui_elements: List[str]) -> str:
        """Create a CSS selector from UI elements"""
        if not ui_elements:
            return '.main-element'
        # Use the first element or combine multiple elements
        return ui_elements[0] if len(ui_elements) == 1 else ', '.join(ui_elements[:3])

    def _generate_preconditions(self, video_title: str, test_type: TestType) -> List[str]:
        """Generate appropriate preconditions based on test type"""
        base_preconditions = [
            "Application is loaded and accessible",
            "User has necessary permissions"
        ]
        
        type_specific = {
            TestType.FUNCTIONAL: ["User is logged in", "Test data is available"],
            TestType.EDGE_CASE: ["User is on the relevant page", "Input fields are accessible"],
            TestType.CROSS_BROWSER: ["Target browser is installed and updated"],
            TestType.ACCESSIBILITY: ["Accessibility tools are enabled", "Screen reader is available"],
            TestType.PERFORMANCE: ["Performance monitoring tools are enabled", "Network conditions are stable"]
        }
        
        return base_preconditions + type_specific.get(test_type, [])

    def generate_functional_tests(self, processed_video: ProcessedVideo, 
                               requirements: Dict[str, Any] = None) -> List[TestCase]:
        """Generate functional test cases from video content"""
        try:
            test_cases = []
            requirements = requirements or {}
            
            if not processed_video.extracted_flows:
                self.logger.warning(f"No extracted flows found for {processed_video.title}")
                return []
            
            # Query RAG engine for main user flows
            query = f"Main user flows and interactions in {processed_video.title}"
            rag_result = self.rag_engine.query(
                RAGQuery(query=query, top_k=5, similarity_threshold=self.similarity_threshold)
            )
            
            # Generate test cases for each user flow
            for i, flow in enumerate(processed_video.extracted_flows[:self.max_test_cases_per_type]):
                if not flow or not flow.strip():
                    continue
                    
                steps = []
                
                # Extract actions from flow using RAG
                flow_query = f"Specific actions and UI interactions in user flow: {flow[:200]}"
                flow_result = self.rag_engine.query(
                    RAGQuery(query=flow_query, top_k=3, similarity_threshold=self.similarity_threshold)
                )
                
                # Create test steps from relevant segments
                for result in flow_result.results:
                    metadata = result.get('metadata', {})
                    if metadata.get('type') == 'segment':
                        action_desc = metadata.get('action_description', 'perform action')
                        ui_elements = self._extract_ui_elements_from_segment(metadata)
                        
                        steps.append(self._create_test_step(
                            action=action_desc,
                            selector=self._create_selector_from_ui_elements(ui_elements),
                            expected_result=f"Action '{action_desc}' executed successfully",
                            wait_condition="element_visible",
                            screenshot=True
                        ))
                
                # Add validation step
                steps.append(self._create_test_step(
                    action="verify",
                    selector=".result-container, .success-message, .main-content",
                    expected_result="User flow completed successfully",
                    screenshot=True
                ))
                
                # Create test case
                test_case = TestCase(
                    id=self._generate_test_id("func"),
                    title=f"Functional Test - {flow[:50]}..." if len(flow) > 50 else f"Functional Test - {flow}",
                    description=f"Verify user flow: {flow[:200]}..." if len(flow) > 200 else f"Verify user flow: {flow}",
                    test_type=TestType.FUNCTIONAL,
                    priority=Priority.HIGH,
                    preconditions=self._generate_preconditions(processed_video.title, TestType.FUNCTIONAL),
                    steps=steps,
                    expected_results=[
                        "User flow completes successfully",
                        "All UI interactions work as expected",
                        "System responds appropriately to user actions"
                    ],
                    tags=["functional", "user-flow", f"flow-{i+1}"],
                    browser_compatibility=["chrome", "firefox", "safari"],
                    estimated_duration=len(steps) * 15 + 30  # 15 seconds per step + 30 seconds setup
                )
                test_cases.append(test_case)
                
            self.logger.info(f"Generated {len(test_cases)} functional test cases")
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Error generating functional tests: {e}")
            return []

    def generate_edge_case_tests(self, processed_video: ProcessedVideo, 
                              requirements: Dict[str, Any] = None) -> List[TestCase]:
        """Generate edge case test cases from video content"""
        try:
            test_cases = []
            requirements = requirements or {}
            
            # Enhanced edge case scenarios with test data
            edge_scenarios = [
                {
                    "name": "empty input",
                    "test_value": "",
                    "description": "Test behavior with empty input fields"
                },
                {
                    "name": "maximum input length",
                    "test_value": "a" * 1000,
                    "description": "Test behavior with maximum length input"
                },
                {
                    "name": "special characters",
                    "test_value": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
                    "description": "Test behavior with special characters"
                },
                {
                    "name": "invalid format",
                    "test_value": "invalid-format-data",
                    "description": "Test behavior with invalid format input"
                },
                {
                    "name": "sql injection attempt",
                    "test_value": "'; DROP TABLE users; --",
                    "description": "Test security against SQL injection"
                },
                {
                    "name": "xss attempt",
                    "test_value": "<script>alert('xss')</script>",
                    "description": "Test security against XSS attacks"
                }
            ]
            
            for scenario in edge_scenarios:
                query = f"Input validation and form handling in {processed_video.title}"
                rag_result = self.rag_engine.query(
                    RAGQuery(query=query, top_k=3, similarity_threshold=self.similarity_threshold)
                )
                
                steps = []
                
                # Look for input elements from RAG results
                input_selectors = []
                for result in rag_result.results:
                    metadata = result.get('metadata', {})
                    if metadata.get('type') == 'segment':
                        ui_elements = self._extract_ui_elements_from_segment(metadata)
                        input_selectors.extend(ui_elements)
                
                # If no specific inputs found, use common input selectors
                if not input_selectors:
                    input_selectors = ['input[type="text"]', 'textarea', '.input-field']
                
                for selector in input_selectors[:3]:  # Limit to first 3 inputs
                    steps.extend([
                        self._create_test_step(
                            action="clear",
                            selector=selector,
                            expected_result="Input field cleared"
                        ),
                        self._create_test_step(
                            action="type",
                            selector=selector,
                            value=scenario["test_value"],
                            expected_result=f"Input accepts or rejects {scenario['name']} appropriately",
                            wait_condition="element_visible",
                            screenshot=True
                        ),
                        self._create_test_step(
                            action="click",
                            selector="button[type='submit'], .submit-button, .save-button",
                            expected_result="Form submission handled correctly",
                            wait_condition="element_clickable",
                            screenshot=True
                        )
                    ])
                
                # Add validation step
                steps.append(self._create_test_step(
                    action="verify",
                    selector=".error-message, .validation-error, .alert",
                    expected_result=f"Appropriate validation message displayed for {scenario['name']}",
                    screenshot=True
                ))
                
                test_case = TestCase(
                    id=self._generate_test_id("edge"),
                    title=f"Edge Case Test - {scenario['name'].title()}",
                    description=scenario["description"],
                    test_type=TestType.EDGE_CASE,
                    priority=Priority.HIGH if "injection" in scenario['name'] or "xss" in scenario['name'] else Priority.MEDIUM,
                    preconditions=self._generate_preconditions(processed_video.title, TestType.EDGE_CASE),
                    steps=steps,
                    expected_results=[
                        f"System handles {scenario['name']} correctly",
                        "Appropriate error messages are displayed",
                        "Security vulnerabilities are prevented"
                    ],
                    tags=["edge-case", "validation", scenario['name'].replace(" ", "-")],
                    browser_compatibility=["chrome"],
                    estimated_duration=len(steps) * 10 + 20
                )
                test_cases.append(test_case)
                
            self.logger.info(f"Generated {len(test_cases)} edge case test cases")
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Error generating edge case tests: {e}")
            return []

    def generate_cross_browser_tests(self, processed_video: ProcessedVideo, 
                                  requirements: Dict[str, Any] = None) -> List[TestCase]:
        """Generate cross-browser compatibility test cases"""
        try:
            test_cases = []
            requirements = requirements or {}
            
            # Browser configurations with specific considerations
            browsers = [
                {"name": "chrome", "version": "latest", "considerations": ["CSS Grid", "Flexbox"]},
                {"name": "firefox", "version": "latest", "considerations": ["CSS Variables", "WebRTC"]},
                {"name": "safari", "version": "latest", "considerations": ["WebKit specific features"]},
                {"name": "edge", "version": "latest", "considerations": ["Chromium compatibility"]}
            ]
            
            # Get key interactions from video
            query = f"Key UI interactions and visual elements in {processed_video.title}"
            rag_result = self.rag_engine.query(
                RAGQuery(query=query, top_k=5, similarity_threshold=self.similarity_threshold)
            )
            
            for browser in browsers:
                steps = []
                
                # Add browser-specific setup
                steps.append(self._create_test_step(
                    action="open_browser",
                    selector=f"browser:{browser['name']}",
                    expected_result=f"{browser['name']} browser opens successfully"
                ))
                
                # Add navigation step
                steps.append(self._create_test_step(
                    action="navigate",
                    selector="url",
                    value=processed_video.url,
                    expected_result="Page loads successfully",
                    wait_condition="page_loaded",
                    screenshot=True
                ))
                
                # Create test steps from RAG results
                for result in rag_result.results:
                    metadata = result.get('metadata', {})
                    if metadata.get('type') == 'segment':
                        action_desc = metadata.get('action_description', 'interact with element')
                        ui_elements = self._extract_ui_elements_from_segment(metadata)
                        
                        steps.append(self._create_test_step(
                            action=action_desc,
                            selector=self._create_selector_from_ui_elements(ui_elements),
                            expected_result=f"UI element renders and functions correctly in {browser['name']}",
                            wait_condition="element_visible",
                            screenshot=True
                        ))
                
                # Add browser-specific validation
                steps.append(self._create_test_step(
                    action="verify_layout",
                    selector=".main-content, .container, body",
                    expected_result=f"Layout renders correctly in {browser['name']}",
                    screenshot=True
                ))
                
                test_case = TestCase(
                    id=self._generate_test_id("browser"),
                    title=f"Cross-Browser Test - {browser['name'].title()}",
                    description=f"Verify UI compatibility and functionality in {browser['name']}",
                    test_type=TestType.CROSS_BROWSER,
                    priority=Priority.MEDIUM,
                    preconditions=self._generate_preconditions(processed_video.title, TestType.CROSS_BROWSER) + 
                                 [f"{browser['name']} browser version {browser['version']} is installed"],
                    steps=steps,
                    expected_results=[
                        "UI elements render correctly",
                        "Interactions work as expected",
                        "No browser-specific issues occur",
                        "Performance is acceptable"
                    ],
                    tags=["cross-browser", browser['name'], "compatibility"],
                    browser_compatibility=[browser['name']],
                    estimated_duration=len(steps) * 12 + 45
                )
                test_cases.append(test_case)
                
            self.logger.info(f"Generated {len(test_cases)} cross-browser test cases")
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Error generating cross-browser tests: {e}")
            return []

    def generate_accessibility_tests(self, processed_video: ProcessedVideo, 
                                  requirements: Dict[str, Any] = None) -> List[TestCase]:
        """Generate accessibility test cases"""
        try:
            test_cases = []
            requirements = requirements or {}
            
            # Enhanced accessibility checks with WCAG guidelines
            a11y_checks = [
                {
                    "name": "keyboard navigation",
                    "description": "Verify all interactive elements are keyboard accessible",
                    "wcag_level": "AA",
                    "tools": ["Tab key", "Arrow keys", "Enter key"]
                },
                {
                    "name": "screen reader compatibility",
                    "description": "Verify content is readable by screen readers",
                    "wcag_level": "AA",
                    "tools": ["NVDA", "JAWS", "VoiceOver"]
                },
                {
                    "name": "color contrast",
                    "description": "Verify sufficient color contrast ratios",
                    "wcag_level": "AA",
                    "tools": ["Color Contrast Analyzer"]
                },
                {
                    "name": "aria labels",
                    "description": "Verify proper ARIA labels and attributes",
                    "wcag_level": "AA",
                    "tools": ["axe-core", "WAVE"]
                },
                {
                    "name": "focus indicators",
                    "description": "Verify visible focus indicators",
                    "wcag_level": "AA",
                    "tools": ["Manual testing"]
                },
                {
                    "name": "alt text",
                    "description": "Verify images have appropriate alt text",
                    "wcag_level": "A",
                    "tools": ["Screen reader", "Inspector"]
                }
            ]
            
            for check in a11y_checks:
                query = f"Accessibility features and interactive elements in {processed_video.title}"
                rag_result = self.rag_engine.query(
                    RAGQuery(query=query, top_k=3, similarity_threshold=self.similarity_threshold)
                )
                
                steps = []
                
                # Add check-specific steps
                if check["name"] == "keyboard navigation":
                    steps.extend([
                        self._create_test_step(
                            action="press_key",
                            selector="body",
                            value="Tab",
                            expected_result="Focus moves to next interactive element",
                            screenshot=True
                        ),
                        self._create_test_step(
                            action="verify_focus",
                            selector=":focus",
                            expected_result="Focus indicator is visible and clear",
                            screenshot=True
                        )
                    ])
                elif check["name"] == "screen reader compatibility":
                    steps.extend([
                        self._create_test_step(
                            action="enable_screen_reader",
                            selector="assistive_tech",
                            expected_result="Screen reader is active"
                        ),
                        self._create_test_step(
                            action="navigate_with_screen_reader",
                            selector=".main-content",
                            expected_result="Content is read aloud correctly",
                            screenshot=True
                        )
                    ])
                elif check["name"] == "color contrast":
                    steps.append(self._create_test_step(
                        action="check_contrast",
                        selector="*",
                        expected_result="Color contrast ratio meets WCAG AA standards (4.5:1)",
                        screenshot=True
                    ))
                elif check["name"] == "aria labels":
                    steps.append(self._create_test_step(
                        action="verify_aria",
                        selector="[aria-label], [aria-labelledby], [aria-describedby]",
                        expected_result="ARIA attributes are present and meaningful",
                        screenshot=True
                    ))
                
                # Add steps from RAG results
                for result in rag_result.results:
                    metadata = result.get('metadata', {})
                    if metadata.get('type') == 'segment':
                        ui_elements = self._extract_ui_elements_from_segment(metadata)
                        
                        steps.append(self._create_test_step(
                            action=f"verify_{check['name'].replace(' ', '_')}",
                            selector=self._create_selector_from_ui_elements(ui_elements),
                            expected_result=f"{check['name']} requirements met for element",
                            screenshot=True
                        ))
                
                test_case = TestCase(
                    id=self._generate_test_id("a11y"),
                    title=f"Accessibility Test - {check['name'].title()}",
                    description=f"{check['description']} (WCAG {check['wcag_level']})",
                    test_type=TestType.ACCESSIBILITY,
                    priority=Priority.HIGH,
                    preconditions=self._generate_preconditions(processed_video.title, TestType.ACCESSIBILITY) + 
                                 [f"Accessibility testing tools available: {', '.join(check['tools'])}"],
                    steps=steps,
                    expected_results=[
                        f"{check['name']} meets WCAG {check['wcag_level']} standards",
                        "No accessibility barriers detected",
                        "Users with disabilities can access content"
                    ],
                    tags=["accessibility", check['name'].replace(" ", "-"), f"wcag-{check['wcag_level'].lower()}"],
                    browser_compatibility=["chrome", "firefox"],
                    estimated_duration=len(steps) * 15 + 60
                )
                test_cases.append(test_case)
                
            self.logger.info(f"Generated {len(test_cases)} accessibility test cases")
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Error generating accessibility tests: {e}")
            return []

    def generate_performance_tests(self, processed_video: ProcessedVideo, 
                                requirements: Dict[str, Any] = None) -> List[TestCase]:
        """Generate performance test cases"""
        try:
            test_cases = []
            requirements = requirements or {}
            
            # Enhanced performance metrics with thresholds
            perf_metrics = [
                {
                    "name": "page load time",
                    "description": "Measure complete page load time",
                    "threshold": "< 3 seconds",
                    "tools": ["Lighthouse", "WebPageTest"]
                },
                {
                    "name": "first contentful paint",
                    "description": "Measure time to first meaningful content",
                    "threshold": "< 1.5 seconds",
                    "tools": ["Lighthouse", "Chrome DevTools"]
                },
                {
                    "name": "interaction response time",
                    "description": "Measure UI interaction response time",
                    "threshold": "< 100ms",
                    "tools": ["Chrome DevTools", "Custom timers"]
                },
                {
                    "name": "resource loading",
                    "description": "Measure resource loading performance",
                    "threshold": "< 2 seconds",
                    "tools": ["Network tab", "Resource timing API"]
                },
                {
                    "name": "memory usage",
                    "description": "Monitor memory consumption",
                    "threshold": "< 100MB",
                    "tools": ["Chrome DevTools Memory tab"]
                }
            ]
            
            for metric in perf_metrics:
                query = f"Performance characteristics and resource usage in {processed_video.title}"
                rag_result = self.rag_engine.query(
                    RAGQuery(query=query, top_k=3, similarity_threshold=self.similarity_threshold)
                )
                
                steps = []
                
                # Add metric-specific measurement steps
                steps.extend([
                    self._create_test_step(
                        action="start_performance_monitoring",
                        selector="performance_tools",
                        expected_result="Performance monitoring tools activated"
                    ),
                    self._create_test_step(
                        action="clear_cache",
                        selector="browser_cache",
                        expected_result="Browser cache cleared"
                    ),
                    self._create_test_step(
                        action="navigate",
                        selector="url",
                        value=processed_video.url,
                        expected_result="Page navigation initiated",
                        wait_condition="page_loaded"
                    ),
                    self._create_test_step(
                        action=f"measure_{metric['name'].replace(' ', '_')}",
                        selector=".main-content",
                        expected_result=f"{metric['name']} measurement completed",
                        screenshot=True
                    )
                ])
                
                # Add interaction steps from RAG results
                for result in rag_result.results:
                    metadata = result.get('metadata', {})
                    if metadata.get('type') == 'segment':
                        action_desc = metadata.get('action_description', 'interact with element')
                        ui_elements = self._extract_ui_elements_from_segment(metadata)
                        
                        steps.append(self._create_test_step(
                            action=action_desc,
                            selector=self._create_selector_from_ui_elements(ui_elements),
                            expected_result=f"Interaction completes within performance threshold",
                            wait_condition="element_stable"
                        ))
                
                # Add validation step
                steps.append(self._create_test_step(
                    action="validate_performance",
                    selector="performance_metrics",
                    expected_result=f"{metric['name']} {metric['threshold']}",
                    screenshot=True
                ))
                
                test_case = TestCase(
                    id=self._generate_test_id("perf"),
                    title=f"Performance Test - {metric['name'].title()}",
                    description=f"{metric['description']} (Target: {metric['threshold']})",
                    test_type=TestType.PERFORMANCE,
                    priority=Priority.MEDIUM,
                    preconditions=self._generate_preconditions(processed_video.title, TestType.PERFORMANCE) + 
                                 [f"Performance testing tools available: {', '.join(metric['tools'])}"],
                    steps=steps,
                    expected_results=[
                        f"{metric['name']} meets performance criteria {metric['threshold']}",
                        "No performance regressions detected",
                        "User experience remains smooth"
                    ],
                    tags=["performance", metric['name'].replace(" ", "-"), "measurement"],
                    browser_compatibility=["chrome"],
                    estimated_duration=len(steps) * 20 + 90
                )
                test_cases.append(test_case)
                
            self.logger.info(f"Generated {len(test_cases)} performance test cases")
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Error generating performance tests: {e}")
            return []

    def get_generator_stats(self) -> Dict[str, Any]:
        """Get generator statistics"""
        return {
            'config': self.config,
            'max_test_cases_per_type': self.max_test_cases_per_type,
            'similarity_threshold': self.similarity_threshold,
            'supported_test_types': [t.value for t in TestType]
        }