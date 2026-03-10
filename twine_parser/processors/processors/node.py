"""
Процессор для тега [NODE]
Создает новую ноду или обновляет существующую
"""

from typing import Optional, Dict, Any, Tuple, List

from ...models.node import Node, NodeType
from ...parsers.tag_parser import TagType
from ..tag_processor import TagProcessor, ProcessingContext


class NodeProcessor(TagProcessor):
    """
    Обработчик тега [NODE]
    
    Форматы:
    - [NODE] node_id
    - [NODE] {"id": "node_id", "type": "dialogue"}
    """
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type == TagType.NODE
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        # Определяем ID ноды
        node_id = None
        node_type = NodeType.DIALOGUE
        node_title = ""
        
        if params:
            # Формат с параметрами
            node_id = params.get('id') or params.get('name')
            node_type_str = params.get('type', 'dialogue')
            node_title = params.get('title', '')
            
            # Конвертируем тип
            try:
                node_type = NodeType(node_type_str)
            except ValueError:
                errors.append(f"Invalid node type: {node_type_str}")
        else:
            # Простой формат: [NODE] node_id
            node_id = value.strip() if value else None
        
        if not node_id:
            errors.append("Node ID is required")
            node_id = f"node_{line_number}"
        
        # Проверяем, существует ли уже такая нода
        existing_node = context.get_node(node_id)
        
        if existing_node:
            # Обновляем существующую ноду
            node = existing_node
            if node_title:
                node.title = node_title
            if node_type != NodeType.DIALOGUE:
                node.type = node_type
            self.log_debug(f"Updated existing node: {node_id}", context)
        else:
            # Создаем новую ноду
            node = Node(
                id=node_id,
                type=node_type,
                title=node_title
            )
            self.log_debug(f"Created new node: {node_id}", context)
        
        return node, errors if errors else None


# Экспортируем экземпляр процессора
processor = NodeProcessor()