"""
Процессор для тегов навигации: [GOTO] и [[link]]
Устанавливает переходы к другим нодам
"""

from typing import Optional, Dict, Any, Tuple, List

from ...models.node import Node
from ...parsers.tag_parser import TagType
from ..tag_processor import TagProcessor, ProcessingContext


class GotoProcessor(TagProcessor):
    """
    Обработчик тегов навигации
    
    Форматы:
    - [GOTO] node_id
    - [GOTO] {"target": "node_id", "condition": "..."}
    - [[node_id]] (в тексте)
    """
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [TagType.GOTO, TagType.LINK]
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        if tag_type == TagType.GOTO:
            # Обработка [GOTO]
            return self._process_goto(value, params, context, errors)
        else:
            # Обработка [[link]] (будет обработана в контенте)
            # Здесь просто пропускаем
            return context.current_node, None
    
    def _process_goto(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [GOTO] тег"""
        
        target_node = None
        condition = None
        
        if params:
            # Формат с параметрами
            target_node = params.get('target') or params.get('goto')
            condition = params.get('condition')
        elif value:
            # Простой формат: [GOTO] node_id
            target_node = value.strip()
        
        if not target_node:
            errors.append("GOTO target is required")
            return context.current_node, errors
        
        # Проверяем, существует ли целевая нода
        if target_node not in context.all_nodes:
            errors.append(f"GOTO target '{target_node}' not found in nodes")
            self.log_debug(f"Warning: target node '{target_node}' not found", context)
        
        if condition:
            # Условный переход
            context.current_node.condition = {
                "type": "if",
                "condition": condition,
                "then": target_node
            }
            self.log_debug(f"Set conditional goto: if {condition} -> {target_node}", context)
        else:
            # Безусловный переход
            context.current_node.next_node_default = target_node
            self.log_debug(f"Set default goto: {target_node}", context)
        
        return context.current_node, errors if errors else None
    
    def extract_links_from_text(self, text: str) -> List[str]:
        """Извлекает ссылки [[link]] из текста"""
        from ...parsers.tag_parser import TagParser
        return TagParser.extract_links(text)


# Экспортируем экземпляр процессора
processor = GotoProcessor()