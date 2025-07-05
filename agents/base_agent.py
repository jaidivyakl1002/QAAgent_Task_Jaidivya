from abc import ABC, abstractmethod
from typing import Dict, Any
import logging
from models.test_case import AgentResponse

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all QA agents"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"Agent.{name}")
        
    @abstractmethod
    def process(self, input_data: Any) -> AgentResponse:
        """Process input data and return response"""
        pass
    
    def validate_input(self, input_data: Any, expected_type: type) -> bool:
        """Validate input data type"""
        if not isinstance(input_data, expected_type):
            self.logger.error(f"Invalid input type. Expected {expected_type}, got {type(input_data)}")
            return False
        return True
    
    def create_success_response(self, message: str, data: Dict[str, Any] = None) -> AgentResponse:
        """Create a successful response"""
        return AgentResponse(
            success=True,
            message=message,
            data=data or {}
        )
    
    def create_error_response(self, message: str, error: str = None) -> AgentResponse:
        """Create an error response"""
        return AgentResponse(
            success=False,
            message=message,
            error=error or message
        )
    
    def log_operation(self, operation: str, details: Dict[str, Any] = None):
        """Log agent operation"""
        self.logger.info(f"Agent {self.name} - {operation}: {details or {}}")
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set_config(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            'name': self.name,
            'config': self.config,
            'status': 'active'
        }