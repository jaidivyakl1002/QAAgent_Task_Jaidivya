from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class TestType(Enum):
    FUNCTIONAL = "functional"
    EDGE_CASE = "edge_case"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"
    CROSS_BROWSER = "cross_browser"

class Priority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class TestStep:
    action: str
    selector: str
    value: Optional[str] = None
    expected_result: Optional[str] = None
    wait_condition: Optional[str] = None

@dataclass
class TestCase:
    id: str
    title: str
    description: str
    test_type: TestType
    priority: Priority
    preconditions: List[str]
    steps: List[TestStep]
    expected_results: List[str]
    tags: List[str]
    browser_compatibility: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'test_type': self.test_type.value,
            'priority': self.priority.value,
            'preconditions': self.preconditions,
            'steps': [step.__dict__ for step in self.steps],
            'expected_results': self.expected_results,
            'tags': self.tags,
            'browser_compatibility': self.browser_compatibility
        }