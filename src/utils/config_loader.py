"""Configuration loader with environment variable support"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
import re
from dotenv import load_dotenv

# Load .env file at module import
load_dotenv()


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file with environment variable substitution
    
    Args:
        config_path: Path to config file. Defaults to config/config.yaml
        
    Returns:
        Configuration dictionary
    """
    if config_path is None:
        # Default to config/config.yaml in project root
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "config.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Load YAML
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Substitute environment variables
    config = _substitute_env_vars(config)
    
    return config


def _substitute_env_vars(config: Any) -> Any:
    """
    Recursively substitute ${VAR_NAME} with environment variables
    
    Args:
        config: Configuration dictionary or value
        
    Returns:
        Configuration with substituted values
    """
    if isinstance(config, dict):
        return {k: _substitute_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_substitute_env_vars(item) for item in config]
    elif isinstance(config, str):
        # Find all ${VAR_NAME} patterns
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, config)
        
        result = config
        for var_name in matches:
            env_value = os.getenv(var_name, '')
            result = result.replace(f'${{{var_name}}}', env_value)
        
        return result
    else:
        return config


def get_api_key() -> str:
    """Get OpenAI API key from environment"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment. "
            "Please set it in .env file or as environment variable."
        )
    return api_key

