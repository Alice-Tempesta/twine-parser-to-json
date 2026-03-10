"""
Twine to Game Engine JSON Parser
Converts Twine HTML files to structured JSON for the game engine
"""

__version__ = "1.0.0"
__author__ = "Alice Tempesta"

from .models.story import Story, StoryMetadata
from .models.episode import Episode, EpisodeMetadata, EpisodeState
from .models.node import Node, NodeType, Choice, Effect, InvestigationPoint
from .models.flag import GlobalFlag, VariableType, VariableOperation
from .config import ParserConfig
from .main import main

__all__ = [
    # Models
    "Story",
    "StoryMetadata",
    "Episode",
    "EpisodeMetadata",
    "EpisodeState",
    "Node",
    "NodeType",
    "Choice",
    "Effect",
    "InvestigationPoint",
    "GlobalFlag",
    "VariableType",
    "VariableOperation",
    
    # Config
    "ParserConfig",
    
    # Main function
    "main",
]