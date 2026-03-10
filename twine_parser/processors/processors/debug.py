"""
Процессор для отладочных тегов: [GET_GLOBAL], [GET_INVENTORY], [DEBUG]
Помогает в отладке игровой логики
"""

from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime

from ...models.node import Node, ContentItem, ContentType
from ...parsers.tag_parser import TagType, TagParser
from ..tag_processor import TagProcessor, ProcessingContext


class DebugProcessor(TagProcessor):
    """
    Обработчик отладочных тегов
    
    Форматы:
    - [DEBUG] Сообщение для отладки
    - [DEBUG] {"message": "...", "level": "info", "variables": true}
    
    - [GET_GLOBAL] variable_name
    - [GET_GLOBAL] {"name": "variable", "format": "json"}
    
    - [GET_INVENTORY] 
    - [GET_INVENTORY] {"format": "list", "filter": "type"}
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.debug_mode = config.get('debug_mode', False) if config else False
        self.debug_messages = []
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [TagType.DEBUG, TagType.GET_GLOBAL, TagType.GET_INVENTORY]
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        # Если не в режиме отладки, игнорируем теги
        if not self.debug_mode and tag_type != TagType.DEBUG:
            return context.current_node, None
        
        if tag_type == TagType.DEBUG:
            return self._process_debug(value, params, context, errors)
        elif tag_type == TagType.GET_GLOBAL:
            return self._process_get_global(value, params, context, errors)
        elif tag_type == TagType.GET_INVENTORY:
            return self._process_get_inventory(value, params, context, errors)
        
        return context.current_node, errors
    
    def _process_debug(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [DEBUG] тег - отладочное сообщение"""
        
        message = None
        level = 'info'
        show_variables = False
        show_inventory = False
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if params:
            message = params.get('message') or params.get('text')
            level = params.get('level', 'info')
            show_variables = params.get('variables', False)
            show_inventory = params.get('inventory', False)
        elif value:
            message = value.strip()
        
        debug_info = []
        
        if message:
            debug_info.append(f"[{timestamp}] [{level.upper()}] {message}")
        
        if show_variables and hasattr(context, 'variables'):
            debug_info.append("Variables:")
            for var_name, var_value in context.variables.items():
                debug_info.append(f"  ${var_name} = {var_value}")
        
        if show_inventory and hasattr(context, 'inventory'):
            debug_info.append("Inventory:")
            for item_id, item in context.inventory.items():
                if hasattr(item, 'quantity'):
                    debug_info.append(f"  {item.name} x{item.quantity}")
                else:
                    debug_info.append(f"  {item}")
        
        if debug_info:
            debug_text = "\n".join(debug_info)
            
            # Добавляем как специальный контент для отладки
            content_item = ContentItem(
                type=ContentType.DEBUG,
                text=debug_text,
                description=f"Debug: {level}"
            )
            
            context.current_node.add_content(content_item)
            
            # Сохраняем в истории отладки
            self.debug_messages.append({
                'timestamp': timestamp,
                'level': level,
                'message': message,
                'node': context.current_node.id,
                'line': line_number
            })
            
            self.log_debug(f"Debug message: {message}", context)
        
        return context.current_node, errors if errors else None
    
    def _process_get_global(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [GET_GLOBAL] тег - просмотр значения переменной"""
        
        var_name = None
        format_type = 'value'  # value, json, string
        
        if params:
            var_name = params.get('name') or params.get('variable')
            format_type = params.get('format', 'value')
        elif value:
            var_name = value.strip()
        
        if not var_name:
            errors.append("Variable name is required for GET_GLOBAL")
            return context.current_node, errors
        
        # Получаем значение переменной
        var_value = None
        if hasattr(context, 'variables') and var_name in context.variables:
            var_value = context.variables[var_name]
        
        if var_value is None:
            var_value = f"<undefined>"
        
        # Форматируем вывод
        output = ""
        if format_type == 'value':
            output = f"${var_name} = {var_value}"
        elif format_type == 'json':
            import json
            try:
                output = json.dumps({var_name: var_value}, indent=2, ensure_ascii=False)
            except:
                output = f"${var_name} = {var_value}"
        else:
            output = str(var_value)
        
        # Добавляем как отладочный контент
        content_item = ContentItem(
            type=ContentType.DEBUG,
            text=output,
            description=f"GET_GLOBAL: {var_name}"
        )
        
        context.current_node.add_content(content_item)
        
        self.log_debug(f"GET_GLOBAL: ${var_name} = {var_value}", context)
        
        return context.current_node, errors if errors else None
    
    def _process_get_inventory(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [GET_INVENTORY] тег - просмотр инвентаря"""
        
        format_type = 'list'  # list, count, json
        filter_type = None
        
        if params:
            format_type = params.get('format', 'list')
            filter_type = params.get('filter')
        
        # Получаем инвентарь
        inventory = []
        if hasattr(context, 'inventory'):
            inventory = context.inventory
        elif hasattr(self, 'inventory'):
            inventory = self.inventory
        
        # Фильтруем если нужно
        if filter_type and inventory:
            filtered = {}
            for item_id, item in inventory.items():
                if hasattr(item, 'type') and item.type == filter_type:
                    filtered[item_id] = item
                elif filter_type == 'stackable' and hasattr(item, 'stackable') and item.stackable:
                    filtered[item_id] = item
            inventory = filtered
        
        # Форматируем вывод
        output = ""
        if format_type == 'list':
            lines = ["Inventory:"]
            for item_id, item in inventory.items():
                if hasattr(item, 'quantity') and item.quantity > 1:
                    lines.append(f"  {item.name} x{item.quantity}")
                else:
                    lines.append(f"  {item.name}")
            output = "\n".join(lines)
        
        elif format_type == 'count':
            count = len(inventory)
            total_items = sum(getattr(item, 'quantity', 1) for item in inventory.values())
            output = f"Items: {count} unique, {total_items} total"
        
        elif format_type == 'json':
            import json
            inventory_dict = {}
            for item_id, item in inventory.items():
                if hasattr(item, 'to_dict'):
                    inventory_dict[item_id] = item.to_dict()
                else:
                    inventory_dict[item_id] = str(item)
            output = json.dumps(inventory_dict, indent=2, ensure_ascii=False)
        
        # Добавляем как отладочный контент
        content_item = ContentItem(
            type=ContentType.DEBUG,
            text=output,
            description="GET_INVENTORY"
        )
        
        context.current_node.add_content(content_item)
        
        self.log_debug(f"GET_INVENTORY: {len(inventory)} items", context)
        
        return context.current_node, errors if errors else None
    
    def get_debug_messages(self) -> List[Dict]:
        """Возвращает все отладочные сообщения"""
        return self.debug_messages
    
    def clear_debug_messages(self):
        """Очищает историю отладки"""
        self.debug_messages.clear()
    
    def set_debug_mode(self, enabled: bool):
        """Включает/выключает режим отладки"""
        self.debug_mode = enabled


# Экспортируем экземпляр процессора
processor = DebugProcessor()