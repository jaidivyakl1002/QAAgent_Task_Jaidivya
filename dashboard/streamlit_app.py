import streamlit as st
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import time
import pandas as pd
from typing import Dict, Any, List
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Import your pipeline
from main import QAAgentPipeline

# Page config
st.set_page_config(
    page_title="QAgenie - AI QA Agent",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .main-header h1 {
        font-size: 3rem;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        font-size: 1.2rem;
        margin-top: 0.5rem;
        opacity: 0.9;
    }
    
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    
    .success-box {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .error-box {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .info-box {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    .sidebar-info {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
            
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'pipeline' not in st.session_state:
    st.session_state.pipeline = None
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'results' not in st.session_state:
    st.session_state.results = None
if 'processing_mode' not in st.session_state:
    st.session_state.processing_mode = None

def init_pipeline():
    """Initialize the QA Agent Pipeline"""
    if st.session_state.pipeline is None:
        try:
            st.session_state.pipeline = QAAgentPipeline()
            return True
        except Exception as e:
            st.error(f"Failed to initialize pipeline: {str(e)}")
            return False
    return True

def display_header():
    """Display the main header"""
    st.markdown("""
    <div class="main-header">
        <h1>🧪 QAgenie</h1>
        <p>AI-Powered Multi-Tool QA Agent for End-to-End Frontend Testing</p>
    </div>
    """, unsafe_allow_html=True)

def display_sidebar():
    """Display sidebar with options and info"""
    st.sidebar.markdown("## 🎯 Processing Options")
    
    # Mode selection
    mode = st.sidebar.selectbox(
        "Select Processing Mode",
        ["🎯 Recruiter.ai (YouTube Video)", "🎬 Custom Video URL", "📁 Generate Scripts from Test Cases"],
        help="Choose how you want to process your tests"
    )
    
    st.sidebar.markdown("---")
    
    # Mode-specific options
    if "Recruiter.ai" in mode:
        
        pipeline_mode = st.sidebar.selectbox(
            "Pipeline Mode",
            ["🚀 Full Pipeline", "🎯 Generate Test Cases Only"],
            help="Choose processing depth"
        )
        
        return {
            'type': 'recruiter_ai',
            'pipeline_mode': 'full' if 'Full' in pipeline_mode else 'generate_only'
        }
    
    elif "Custom Video" in mode:
        video_url = st.sidebar.text_input(
            "YouTube Video URL",
            placeholder="https://youtu.be/...",
            help="Enter a valid YouTube URL"
        )
        
        return {
            'type': 'custom_video',
            'video_url': video_url
        }
    
    else:  # Generate Scripts from Test Cases
        test_cases_path = st.sidebar.text_input(
            "Test Cases Path",
            placeholder="/path/to/test_cases.json",
            help="Path to JSON file or directory containing test cases"
        )
        
        test_type = st.sidebar.selectbox(
            "Test Type",
            ["custom", "recruiter_ai"],
            help="Test type for organizing output"
        )
        
        return {
            'type': 'scripts_only',
            'test_cases_path': test_cases_path,
            'test_type': test_type
        }

def display_progress(message: str, progress: float = None):
    """Display simple progress bar"""
    st.markdown(f"🔄 {message}")
    if progress is not None:
        st.progress(progress)

def display_results(results: Dict[str, Any]):
    """Display processing results"""
    if not results:
        return
    
    if results.get('success'):
        st.markdown("""
        <div class="success-box">
            <h3>✅ Processing Completed Successfully!</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Display detailed results
        display_detailed_results(results)
        
        # Display next steps
        display_next_steps(results)
        
    else:
        st.markdown(f"""
        <div class="error-box">
            <h3>❌ Processing Failed</h3>
            <p><strong>Error:</strong> {results.get('message', 'Unknown error')}</p>
            <p><strong>Details:</strong> {results.get('error', 'No details available')}</p>
        </div>
        """, unsafe_allow_html=True)

def display_detailed_results(results: Dict[str, Any]):
    """Display detailed results"""
    st.markdown("## 📋 Detailed Results")
    
    data = results.get('data', {})
    
    # Check if this is a complete pipeline with execution
    if 'execution_result' in data:
        # Full pipeline - show all tabs including reports
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Test Cases", "🎭 Scripts", "📁 Files", "📈 Breakdown", "🔍 Reports"])
        
        with tab1:
            display_test_cases_tab(data)
        
        with tab2:
            display_scripts_tab(data)
        
        with tab3:
            display_files_tab(data)
        
        with tab4:
            display_breakdown_tab(data)
        
        with tab5:
            display_execution_reports(data)
    
    elif 'test_suite' in data:
        # Test generation only
        tab1, tab2 = st.tabs(["📊 Test Cases", "📈 Breakdown"])
        
        with tab1:
            display_test_cases_tab(data)
        
        with tab2:
            display_breakdown_tab(data)
    
    elif 'stats' in data:
        # Script generation only
        tab1, tab2 = st.tabs(["🎭 Scripts", "📁 Files"])
        
        with tab1:
            display_scripts_tab(data)
        
        with tab2:
            display_files_tab(data)

def display_test_cases_tab(data: Dict[str, Any]):
    """Display test cases information"""
    test_suite = data.get('test_suite', {})
    test_cases = test_suite.get('test_cases', [])
    
    if not test_cases:
        st.info("No test cases found in results.")
        return
    
    st.markdown(f"### Generated {len(test_cases)} Test Cases")
    
    # Show first few test cases
    for i, test_case in enumerate(test_cases[:5]):
        with st.expander(f"Test Case {i+1}: {test_case.get('name', 'Unnamed')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Type:** {test_case.get('test_type', 'N/A')}")
                st.markdown(f"**Priority:** {test_case.get('priority', 'N/A')}")
                st.markdown(f"**Category:** {test_case.get('category', 'N/A')}")
            
            with col2:
                st.markdown(f"**Browser:** {test_case.get('browser', 'N/A')}")
                st.markdown(f"**Viewport:** {test_case.get('viewport', 'N/A')}")
            
            if 'description' in test_case:
                st.markdown(f"**Description:** {test_case['description']}")
            
            if 'steps' in test_case:
                st.markdown("**Steps:**")
                for step_num, step in enumerate(test_case['steps'], 1):
                    st.markdown(f"{step_num}. {step}")
    
    if len(test_cases) > 5:
        st.info(f"Showing first 5 test cases. Total: {len(test_cases)}")

def display_scripts_tab(data: Dict[str, Any]):
    """Display scripts information"""
    stats = data.get('stats', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Successful Scripts", stats.get('successful', 0))
        st.metric("Failed Scripts", stats.get('failed', 0))
    
    with col2:
        st.metric("Output Directory", data.get('output_dir', 'N/A'))
        
    if 'conversion_details' in data:
        st.markdown("### Conversion Details")
        details = data['conversion_details']
        
        for detail in details[:10]:  # Show first 10
            status = "✅" if detail.get('success') else "❌"
            st.markdown(f"{status} {detail.get('name', 'Unknown')}")

def display_files_tab(data: Dict[str, Any]):
    """Display generated files information with enhanced folder structure"""
    # Define the base path for generated files
    base_path = r"C:\Users\Jaidivya Kumar Lohan\Desktop\QAAgent_Task_Jaidivya_Kumar_Lohani\playwright_tests\tests\generated\recruter_ai"
    
    # Define the test type folders
    test_folders = {
        "accessibility": "♿ Accessibility Tests",
        "cross_browser": "🌐 Cross Browser Tests", 
        "perfomance": "⚡ Performance Tests",
        "functionality": "🔧 Functionality Tests",
        "edge_cases": "🎯 Edge Cases Tests"
    }
    
    st.markdown("### 📁 Generated Test Files")
    
    # Check if base path exists
    if not os.path.exists(base_path):
        st.warning(f"Generated files directory not found: {base_path}")
        return
    
    total_files = 0
    
    # Display files by category
    for folder_name, display_name in test_folders.items():
        folder_path = os.path.join(base_path, folder_name)
        
        if os.path.exists(folder_path):
            # Get all test files in this folder
            test_files = []
            for file in os.listdir(folder_path):
                if file.endswith(('.js', '.ts', '.spec.js', '.spec.ts', '.test.js', '.test.ts')):
                    test_files.append(file)
            
            if test_files:
                total_files += len(test_files)
                
                with st.expander(f"{display_name} ({len(test_files)} files)"):
                    for file in sorted(test_files):
                        file_path = os.path.join(folder_path, file)
                        
                        # Display file info
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"📄 **{file}**")
                            st.caption(f"Path: {file_path}")
                        
                        with col2:
                            # Add a button to view file content
                            if st.button(f"👁️ View", key=f"view_{folder_name}_{file}"):
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                    
                                    # Show file content in a modal-like expander
                                    with st.expander(f"📖 Content: {file}", expanded=True):
                                        st.code(content, language='javascript')
                                except Exception as e:
                                    st.error(f"Error reading file: {e}")
            else:
                st.info(f"No test files found in {display_name}")
        else:
            st.warning(f"Folder not found: {display_name}")
    
    # Display summary
    if total_files > 0:
        st.success(f"📊 Total Generated Files: {total_files}")
    else:
        st.info("No test files found in the generated directories.")
    
    # Add download option for the entire folder
    if total_files > 0:
        st.markdown("---")
        st.markdown("### 📥 Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📦 View All Files List"):
                st.markdown("#### Complete Files List:")
                for folder_name, display_name in test_folders.items():
                    folder_path = os.path.join(base_path, folder_name)
                    if os.path.exists(folder_path):
                        test_files = [f for f in os.listdir(folder_path) 
                                    if f.endswith(('.js', '.ts', '.spec.js', '.spec.ts', '.test.js', '.test.ts'))]
                        if test_files:
                            st.markdown(f"**{display_name}:**")
                            for file in sorted(test_files):
                                st.markdown(f"  • {file}")
        
        with col2:
            st.info("💡 Tip: Use the 'View' buttons above to inspect individual test files before running them.")

def display_breakdown_tab(data: Dict[str, Any]):
    """Display test breakdown charts"""
    test_suite = data.get('test_suite', {})
    test_cases = test_suite.get('test_cases', [])
    
    if not test_cases:
        st.info("No test cases available for breakdown.")
        return
    
    # Test type breakdown
    test_types = {}
    priorities = {}
    browsers = {}
    
    for test_case in test_cases:
        # Test types
        test_type = test_case.get('test_type', 'functional')
        test_types[test_type] = test_types.get(test_type, 0) + 1
        
        # Priorities
        priority = test_case.get('priority', 'medium')
        priorities[priority] = priorities.get(priority, 0) + 1
        
        # Browsers
        browser = test_case.get('browser', 'chrome')
        browsers[browser] = browsers.get(browser, 0) + 1
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### Test Types")
        for test_type, count in test_types.items():
            st.markdown(f"**{test_type}:** {count}")
    
    with col2:
        st.markdown("#### Priorities")
        for priority, count in priorities.items():
            st.markdown(f"**{priority}:** {count}")
    
    with col3:
        st.markdown("#### Browsers")
        for browser, count in browsers.items():
            st.markdown(f"**{browser}:** {count}")

def display_next_steps(results: Dict[str, Any]):
    """Display next steps"""
    data = results.get('data', {})
    next_steps = data.get('next_steps', [])
    
    if not next_steps:
        return
    
    st.markdown("## 📋 Next Steps")
    
    st.markdown("""
    <div class="info-box">
        <h4>Ready to Execute Tests</h4>
        <p>Your test scripts have been generated and are ready for execution.</p>
    </div>
    """, unsafe_allow_html=True)
    
    for step in next_steps:
        if step.strip():  # Skip empty lines
            st.markdown(f"• {step}")

def process_recruiter_ai(pipeline_mode: str):
    """Process Recruiter.ai video"""
    if pipeline_mode == 'full':
        # Full pipeline
        display_progress("Starting full pipeline: video → test cases → scripts → execution", 0.1)
        time.sleep(1)
        
        display_progress("Downloading and transcribing video...", 0.2)
        time.sleep(4)
        
        display_progress("Processing transcript into structured format...", 0.4)
        time.sleep(8)
        
        display_progress("Generating test cases...", 0.6)
        time.sleep(10)
        
        display_progress("Converting to Playwright scripts...", 0.8)
        time.sleep(10)
        
        display_progress("Executing tests...", 0.9)
        time.sleep(10)
        
        return st.session_state.pipeline.process_recruter_video_complete()
    
    else:
        # Generate only
        display_progress("Downloading and transcribing video...", 0.3)
        time.sleep(1)
        
        display_progress("Processing transcript...", 0.6)
        time.sleep(4)
        
        display_progress("Generating test cases...", 0.9)
        time.sleep(8)
        
        result = st.session_state.pipeline.process_recruter_video()
        
        # Convert AgentResponse to dict
        if hasattr(result, 'success'):
            return {
                'success': result.success,
                'message': result.message,
                'data': result.data,
                'error': result.error
            }
        return result

def process_custom_video(video_url: str):
    """Process custom video URL"""
    if not video_url:
        return {
            'success': False,
            'message': 'Please provide a video URL',
            'error': 'Missing video URL'
        }
    
    display_progress(f"Processing custom video: {video_url}", 0.2)
    time.sleep(3)
    
    display_progress("Downloading video...", 0.4)
    time.sleep(3)
    
    display_progress("Transcribing video...", 0.6)
    time.sleep(5)
    
    display_progress("Generating test cases...", 0.8)
    time.sleep(10)
    
    result = st.session_state.pipeline.run_custom_video(video_url)
    
    # Convert AgentResponse to dict if needed
    if hasattr(result, 'success'):
        return {
            'success': result.success,
            'message': result.message,
            'data': result.data,
            'error': result.error
        }
    return result

def load_execution_reports(reports_dir: str) -> Dict[str, Any]:
    """Load execution reports from the reports directory"""
    reports = {}
    
    try:
        # Load JSON report for data processing
        json_path = os.path.join(reports_dir, "execution_report.json")
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                reports['json'] = json.load(f)
        
        # Load MD report for readable content
        md_path = os.path.join(reports_dir, "execution_report.md")
        if os.path.exists(md_path):
            with open(md_path, 'r') as f:
                reports['markdown'] = f.read()
        
        # Check if HTML report exists
        html_path = os.path.join(reports_dir, "execution_report.html")
        if os.path.exists(html_path):
            reports['html_path'] = html_path
            
    except Exception as e:
        st.error(f"Failed to load reports: {e}")
    
    return reports

def display_execution_reports(data: Dict[str, Any]):
    """Display execution reports after test completion"""
    reports_dir = "C:/Users/Jaidivya Kumar Lohan/Desktop/QAAgent_Task_Jaidivya_Kumar_Lohani/playwright_tests/tests/reports/recruter_ai"
    
    if not os.path.exists(reports_dir):
        st.info("No execution reports found. Run tests to generate reports.")
        return
    
    st.markdown("## 📊 Test Execution Reports")
    
    reports = load_execution_reports(reports_dir)
    
    if not reports:
        st.warning("No valid reports found in the reports directory.")
        return
    
    # Create tabs for different report views
    tab1, tab2, tab3 = st.tabs(["📈 Summary", "📋 Detailed Report", "📁 Files"])
    
    with tab1:
        display_execution_summary(reports)
    
    with tab2:
        display_detailed_report(reports)
    
    with tab3:
        display_report_files(reports_dir)

def display_execution_summary(reports: Dict[str, Any]):
    """Display execution summary from JSON report"""
    if 'json' not in reports:
        st.info("No JSON report available for summary.")
        return
    
    json_data = reports['json']
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tests", json_data.get('total_tests', 0))
    
    with col2:
        st.metric("Passed", json_data.get('passed', 0), 
                 delta=None, delta_color="normal")
    
    with col3:
        st.metric("Failed", json_data.get('failed', 0))
    
    with col4:
        success_rate = (json_data.get('passed', 0) / max(json_data.get('total_tests', 1), 1)) * 100
        st.metric("Success Rate", f"{success_rate:.1f}%")
    
    # Display test results table if available
    if 'test_results' in json_data:
        st.markdown("### Test Results")
        df = pd.DataFrame(json_data['test_results'])
        st.dataframe(df, use_container_width=True)

def display_detailed_report(reports: Dict[str, Any]):
    """Display detailed markdown report"""
    if 'markdown' in reports:
        st.markdown("### Detailed Execution Report")
        st.markdown(reports['markdown'])
    
    # Option to download HTML report
    if 'html_path' in reports:
        with open(reports['html_path'], 'rb') as f:
            st.download_button(
                label="📥 Download HTML Report",
                data=f.read(),
                file_name="execution_report.html",
                mime="text/html"
            )

def display_report_files(reports_dir: str):
    """Display available report files"""
    st.markdown("### Available Report Files")
    
    report_files = [
        ("execution_report.html", "HTML Report"),
        ("execution_report.json", "JSON Data"),
        ("execution_report.md", "Markdown Report")
    ]
    
    for filename, description in report_files:
        filepath = os.path.join(reports_dir, filename)
        if os.path.exists(filepath):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{description}**")
                st.code(filepath, language='text')
            with col2:
                if st.button(f"📥 Download", key=f"download_{filename}"):
                    with open(filepath, 'rb') as f:
                        st.download_button(
                            label=f"Download {filename}",
                            data=f.read(),
                            file_name=filename,
                            mime="text/html" if filename.endswith('.html') else "text/plain"
                        )

def process_scripts_only(test_cases_path: str, test_type: str):
    """Process scripts generation only"""
    if not test_cases_path:
        return {
            'success': False,
            'message': 'Please provide test cases path',
            'error': 'Missing test cases path'
        }
    
    display_progress(f"Loading test cases from: {test_cases_path}", 0.2)
    time.sleep(1)
    
    display_progress("Converting test cases to Playwright scripts...", 0.6)
    time.sleep(1)
    
    display_progress("Saving generated scripts...", 0.8)
    time.sleep(1)
    
    return st.session_state.pipeline.generate_scripts_from_existing_tests(
        test_cases_path, 
        test_type=test_type
    )

def main():
    """Main Streamlit application"""
    display_header()
    
    # Initialize pipeline
    if not init_pipeline():
        st.stop()
    
    # Display sidebar and get configuration
    config = display_sidebar()
    
    st.markdown("---")
    
    # Main processing section
    st.markdown("## 🚀 Start Processing")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if config['type'] == 'recruiter_ai':
            st.markdown("### 🎯 Recruiter.ai Processing")
            st.markdown("Process the official Recruiter.ai how-to video to generate comprehensive test cases.")
            
        elif config['type'] == 'custom_video':
            st.markdown("### 🎬 Custom Video Processing")
            st.markdown("Process any YouTube video URL to generate test cases.")
            
        else:
            st.markdown("### 📁 Script Generation")
            st.markdown("Convert existing test cases into Playwright scripts.")
    
    with col2:
        # Process button
        if st.button("🚀 Start Processing", key="process_btn"):
            if not st.session_state.processing:
                st.session_state.processing = True
                st.session_state.processing_mode = config['type']
                st.session_state.results = None
                st.rerun()
    
    # Processing logic
    if st.session_state.processing:
        try:
            if config['type'] == 'recruiter_ai':
                result = process_recruiter_ai(config['pipeline_mode'])
            elif config['type'] == 'custom_video':
                result = process_custom_video(config['video_url'])
            else:
                result = process_scripts_only(config['test_cases_path'], config['test_type'])
            
            st.session_state.results = result
            st.session_state.processing = False
            st.rerun()
            
        except Exception as e:
            st.session_state.results = {
                'success': False,
                'message': f'Processing failed: {str(e)}',
                'error': str(e)
            }
            st.session_state.processing = False
            st.rerun()
    
    # Display results
    if st.session_state.results:
        display_results(st.session_state.results)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 2rem;">
        <p>🧪 QAgenie - AI-Powered QA Agent | Built with Streamlit</p>
        <p>Automated Frontend Testing • RAG + LLM • Playwright Integration</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()