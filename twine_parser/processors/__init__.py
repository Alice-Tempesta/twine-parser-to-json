"""
Tag processors
Each processor is responsible for a specific type of tags
"""

from .tag_processor import TagProcessor, ProcessingContext

__all__ = [
    'TagProcessor',
    'ProcessingContext',
]