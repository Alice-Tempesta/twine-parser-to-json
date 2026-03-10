"""
Процессор для тега [TITLE]
Устанавливает заголовок текущей ноды
"""

from typing import Optional, Dict, Any, Tuple, List

from ...models.node import Node
from ...parsers.tag_parser import TagType
from ..tag_processor import TagProcessor, ProcessingContext


class TitleProcessor(TagProcessor):
    """
    Обработчик тега [TITLE]
    
    Форматы:
    - [TITLE] Заголовок ноды
    - [TITLE] {"text": "Заголовок"}
    """
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type == TagType.TITLE
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        # Получаем заголовок
        title = None
        if params:
            title = params.get('text') or params.get('title')
        elif value:
            title = value.strip()
        
        if not title:
            errors.append("Title text is required")
            return context.current_node, errors
        
        # Устанавливаем заголовок
        context.current_node.title = title
        
        self.log_debug(f"Set title: '{title}' for node: {context.current_node.id}", context)
        
        return context.current_node, errors if errors else None


# Экспортируем экземпляр процессора
processor = TitleProcessor()