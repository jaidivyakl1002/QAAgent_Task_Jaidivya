from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum

class TestType(str, Enum):
    FUNCTIONAL = "functional"
    EDGE_CASE = "edge_case"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"
    CROSS_BROWSER = "cross_browser"

class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TestStep(BaseModel):
    action: str = Field(..., description="Action to perform (click, type, wait, etc.)")
    selector: str = Field(..., description="CSS selector or element identifier")
    value: Optional[str] = Field(None, description="Value to input (for type actions)")
    expected_result: Optional[str] = Field(None, description="Expected result after this step")
    wait_condition: Optional[str] = Field(None, description="Condition to wait for")
    screenshot: bool = Field(False, description="Whether to take screenshot after this step")

class TestCase(BaseModel):
    id: str = Field(..., description="Unique test case identifier")
    title: str = Field(..., description="Test case title")
    description: str = Field(..., description="Detailed description of what the test does")
    test_type: TestType = Field(..., description="Type of test")
    priority: Priority = Field(..., description="Test priority level")
    preconditions: List[str] = Field(default_factory=list, description="Prerequisites before running test")
    steps: List[TestStep] = Field(..., description="List of test steps")
    expected_results: List[str] = Field(default_factory=list, description="Overall expected results")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    browser_compatibility: List[str] = Field(default_factory=list, description="Compatible browsers")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")
    
    class Config:
        use_enum_values = True

class TestSuite(BaseModel):
    id: str = Field(..., description="Test suite identifier")
    name: str = Field(..., description="Test suite name")
    description: str = Field(..., description="Test suite description")
    test_cases: List[TestCase] = Field(default_factory=list, description="List of test cases")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    source_video: Optional[str] = Field(None, description="Source video URL or path")
    
    class Config:
        use_enum_values = True

class VideoSegment(BaseModel):
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    transcript: str = Field(..., description="Transcript text for this segment")
    action_description: str = Field(..., description="Description of action performed")
    ui_elements: List[str] = Field(default_factory=list, description="UI elements mentioned")
    
class ProcessedVideo(BaseModel):
    url: str = Field(..., description="Video URL")
    title: str = Field(..., description="Video title")
    duration: float = Field(..., description="Video duration in seconds")
    full_transcript: str = Field(..., description="Complete video transcript")
    segments: List[VideoSegment] = Field(default_factory=list, description="Video segments")
    extracted_flows: List[str] = Field(default_factory=list, description="Identified user flows")
    ui_components: List[str] = Field(default_factory=list, description="UI components mentioned")
    
class AgentResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Dict] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if any")
    
class RAGQuery(BaseModel):
    query: str = Field(..., description="Query text")
    top_k: int = Field(5, description="Number of top results to return")
    similarity_threshold: float = Field(0.7, description="Minimum similarity threshold")
    
class RAGResult(BaseModel):
    query: str = Field(..., description="Original query")
    results: List[Dict] = Field(default_factory=list, description="Retrieved results")
    generated_response: Optional[str] = Field(None, description="Generated response")
    confidence: float = Field(0.0, description="Confidence score")