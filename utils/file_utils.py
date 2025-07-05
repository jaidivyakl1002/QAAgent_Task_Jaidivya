import json
from pathlib import Path
from typing import Any, Dict, Union
import logging

logger = logging.getLogger(__name__)

def save_json(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """
    Save dictionary data to a JSON file.
    
    Args:
        data: Dictionary to save as JSON
        file_path: Path to the output JSON file
    """
    try:
        # Convert Path object to string if necessary
        file_path = Path(file_path)
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSON data to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved JSON to {file_path}")
        
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        raise

def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load JSON data from a file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing the loaded JSON data
        
    Raises:
        FileNotFoundError: If the file does not exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Successfully loaded JSON from {file_path}")
        return data
        
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        raise