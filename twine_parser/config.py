"""
Parser configuration
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParserConfig:
    """Parser Configuration"""
    
    # Paths
    input_file: str = ""
    output_dir: str = "output"
    
    # Operating modes
    debug: bool = False
    validate: bool = True
    pretty_json: bool = True
    
    # Parsing options
    split_by_episodes: bool = True  # Split into separate files by episode
    extract_metadata: bool = True # Extract metadata
    process_conditions: bool = True # Process conditions [IF]
    process_effects: bool = True # Process effects [ADD_GLOBAL], etc.
    
    # Options validations
    strict_validation: bool = False# Strict validation (stops on errors)
    check_links: bool = True # Check links
    check_variables: bool = True # Check variables
    
    # Export Options
    indent: int = 2 if pretty_json else None
    ensure_ascii: bool = False
    encoding: str = "utf-8"
    
    # Special tags for processing
    custom_tags: Dict[str, str] = field(default_factory=dict)
    
    # Ignored tags
    ignore_tags: list = field(default_factory=lambda: ["debug", "test"])
    
    def __post_init__(self):
        """Post-processing after initialization"""
        if self.input_file:
            self.input_file = str(Path(self.input_file).absolute())
        
        self.output_dir = str(Path(self.output_dir).absolute())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParserConfig':
        """Creates a configuration from the dictionary""" 
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    @classmethod
    def from_env(cls) -> 'ParserConfig':
        """Creates a configuration from environment variables"""
        config = cls()
        
        # Read from environment variables with the TWINE_ prefix
        for key in cls.__annotations__:
            env_key = f"TWINE_{key.upper()}"
            if env_key in os.environ:
                value = os.environ[env_key]
                
                # Converting types
                if key in ['debug', 'validate', 'pretty_json', 'split_by_episodes',
                          'extract_metadata', 'process_conditions', 'process_effects',
                          'strict_validation', 'check_links', 'check_variables']:
                    value = value.lower() in ['true', '1', 'yes', 'on']
                elif key in ['indent']:
                    value = int(value) if value.isdigit() else None
                
                setattr(config, key, value)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Converts to dictionary"""
        return {
            "input_file": self.input_file,
            "output_dir": self.output_dir,
            "debug": self.debug,
            "validate": self.validate,
            "pretty_json": self.pretty_json,
            "split_by_episodes": self.split_by_episodes,
            "extract_metadata": self.extract_metadata,
            "process_conditions": self.process_conditions,
            "process_effects": self.process_effects,
            "strict_validation": self.strict_validation,
            "check_links": self.check_links,
            "check_variables": self.check_variables,
            "indent": self.indent,
            "encoding": self.encoding
        }
    
    def ensure_output_dir(self) -> Path:
        """Creates an output directory if it does not exist"""
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path