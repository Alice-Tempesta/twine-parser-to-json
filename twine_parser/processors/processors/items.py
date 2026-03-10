"""
Процессор для тегов предметов: [GIVE_ITEM], [REMOVE_ITEM], [CHECK_ITEM]
Управляет инвентарем игрока
"""

from typing import Optional, Dict, Any, Tuple, List
import uuid

from ...models.node import Node, Effect
from ...parsers.tag_parser import TagType, TagParser
from ..tag_processor import TagProcessor, ProcessingContext
from .choice import ChoiceProcessor
from .conditions import ConditionsProcessor


class Item:
    """
    Класс для представления предмета в инвентаре
    """
    def __init__(self, item_id: str, name: str, description: str = "", 
                 icon: str = "", stackable: bool = False, 
                 max_stack: int = 99, properties: Dict = None):
        self.id = item_id
        self.name = name
        self.description = description
        self.icon = icon
        self.stackable = stackable
        self.max_stack = max_stack
        self.properties = properties or {}
        self.quantity = 1
    
    def to_dict(self) -> Dict:
        """Конвертирует в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'stackable': self.stackable,
            'max_stack': self.max_stack,
            'properties': self.properties,
            'quantity': self.quantity
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Item':
        """Создает из словаря"""
        item = cls(
            item_id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            icon=data.get('icon', ''),
            stackable=data.get('stackable', False),
            max_stack=data.get('max_stack', 99),
            properties=data.get('properties', {})
        )
        item.quantity = data.get('quantity', 1)
        return item


class ItemsProcessor(TagProcessor):
    """
    Обработчик тегов предметов
    
    Форматы:
    - [GIVE_ITEM] item_name
    - [GIVE_ITEM] {"id": "key", "name": "Старый ключ", "description": "...", "quantity": 1}
    
    - [REMOVE_ITEM] item_name
    - [REMOVE_ITEM] {"id": "key", "quantity": 1}
    
    - [CHECK_ITEM] item_name
    - [CHECK_ITEM] {"id": "key", "quantity": 1, "condition": "has"}
    """
    
    # Типы проверок предметов
    CHECK_TYPES = {
        'has': 'has_item',      # есть предмет
        'has_not': 'has_not',    # нет предмета
        'quantity': 'quantity',  # проверка количества
        'property': 'property'   # проверка свойства предмета
    }
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.choice_processor = None
        self.conditions_processor = None
        self.inventory = {}  # словарь предметов в инвентаре {item_id: Item}
    
    def set_choice_processor(self, choice_processor: ChoiceProcessor):
        """Устанавливает ссылку на ChoiceProcessor"""
        self.choice_processor = choice_processor
    
    def set_conditions_processor(self, conditions_processor: ConditionsProcessor):
        """Устанавливает ссылку на ConditionsProcessor"""
        self.conditions_processor = conditions_processor
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [
            TagType.GIVE_ITEM,
            TagType.REMOVE_ITEM,
            TagType.CHECK_ITEM
        ]
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        if tag_type == TagType.GIVE_ITEM:
            return self._process_give_item(value, params, context, errors)
        elif tag_type == TagType.REMOVE_ITEM:
            return self._process_remove_item(value, params, context, errors)
        elif tag_type == TagType.CHECK_ITEM:
            return self._process_check_item(value, params, context, errors)
        
        return context.current_node, errors
    
    def _process_give_item(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [GIVE_ITEM] тег - добавление предмета в инвентарь"""
        
        item_data = self._parse_item_data(value, params)
        
        if not item_data:
            errors.append("Failed to parse item data")
            return context.current_node, errors
        
        # Создаем эффект
        effect = {
            "type": "add_item",
            "item": item_data['id'],
            "item_data": item_data,
            "quantity": item_data.get('quantity', 1)
        }
        
        # Проверяем, находимся ли мы внутри блока выбора
        if self.choice_processor and hasattr(self.choice_processor, 'current_choice'):
            if self.choice_processor.current_choice:
                # Добавляем эффект к текущему выбору
                self.choice_processor.add_effect_to_current_choice(effect)
                self.log_debug(f"Added give_item effect to current choice: {item_data['id']}", context)
                return context.current_node, None
        
        # Иначе добавляем как эффект при входе в ноду
        if not hasattr(context.current_node, 'transitions'):
            from ...models.node import Transition
            context.current_node.transitions = Transition()
        
        context.current_node.transitions.on_enter.append(Effect(**effect))
        
        # Добавляем предмет в текущий инвентарь для проверок
        self._add_to_inventory(item_data, context)
        
        self.log_debug(f"Added give_item effect: {item_data['id']} x{item_data.get('quantity', 1)}", context)
        
        return context.current_node, errors if errors else None
    
    def _process_remove_item(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [REMOVE_ITEM] тег - удаление предмета из инвентаря"""
        
        item_id = None
        quantity = 1
        
        if params:
            item_id = params.get('id') or params.get('item')
            quantity = int(params.get('quantity', 1))
        elif value:
            item_id = value.strip()
        
        if not item_id:
            errors.append("Item ID is required for REMOVE_ITEM")
            return context.current_node, errors
        
        # Создаем эффект
        effect = {
            "type": "remove_item",
            "item": item_id,
            "quantity": quantity
        }
        
        # Проверяем, находимся ли мы внутри блока выбора
        if self.choice_processor and hasattr(self.choice_processor, 'current_choice'):
            if self.choice_processor.current_choice:
                # Добавляем эффект к текущему выбору
                self.choice_processor.add_effect_to_current_choice(effect)
                self.log_debug(f"Added remove_item effect to current choice: {item_id}", context)
                return context.current_node, None
        
        # Иначе добавляем как эффект при входе в ноду
        if not hasattr(context.current_node, 'transitions'):
            from ...models.node import Transition
            context.current_node.transitions = Transition()
        
        context.current_node.transitions.on_enter.append(Effect(**effect))
        
        # Удаляем из текущего инвентаря
        self._remove_from_inventory(item_id, quantity, context)
        
        self.log_debug(f"Added remove_item effect: {item_id} x{quantity}", context)
        
        return context.current_node, errors if errors else None
    
    def _process_check_item(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [CHECK_ITEM] тег - проверка наличия предмета"""
        
        item_id = None
        check_type = 'has'
        quantity = 1
        property_name = None
        property_value = None
        
        if params:
            item_id = params.get('id') or params.get('item')
            check_type = params.get('check', 'has')
            quantity = int(params.get('quantity', 1))
            property_name = params.get('property')
            property_value = params.get('value')
        elif value:
            # Простой формат: [CHECK_ITEM] item_name
            item_id = value.strip()
        
        if not item_id:
            errors.append("Item ID is required for CHECK_ITEM")
            return context.current_node, errors
        
        # Создаем условие на основе проверки предмета
        condition = self._create_item_condition(
            item_id, check_type, quantity, property_name, property_value, context
        )
        
        # Добавляем условие в стек условий
        if self.conditions_processor:
            if not hasattr(context, 'conditions_stack'):
                context.conditions_stack = []
            
            context.conditions_stack.append({
                'type': 'if',
                'condition': condition,
                'raw': f"check_item: {item_id}",
                'active': None
            })
            
            self.log_debug(f"Added item check condition: {item_id}", context)
        
        return context.current_node, errors if errors else None
    
    def _parse_item_data(self, value: Optional[str], params: Optional[Dict]) -> Optional[Dict]:
        """
        Парсит данные предмета из value или params
        
        Returns:
            Словарь с данными предмета или None
        """
        if params:
            # Формат с параметрами
            item_data = {
                'id': params.get('id') or params.get('item') or str(uuid.uuid4()),
                'name': params.get('name', params.get('item', 'Unknown Item')),
                'description': params.get('description', ''),
                'icon': params.get('icon', ''),
                'stackable': params.get('stackable', False),
                'max_stack': int(params.get('max_stack', 99)),
                'quantity': int(params.get('quantity', 1)),
                'properties': params.get('properties', {})
            }
            return item_data
        
        elif value:
            # Простой формат: [GIVE_ITEM] item_name
            # Создаем базовый предмет
            item_name = value.strip()
            item_id = item_name.lower().replace(' ', '_')
            
            return {
                'id': item_id,
                'name': item_name,
                'description': '',
                'icon': '',
                'stackable': False,
                'max_stack': 99,
                'quantity': 1,
                'properties': {}
            }
        
        return None
    
    def _create_item_condition(
        self, 
        item_id: str, 
        check_type: str, 
        quantity: int,
        property_name: Optional[str],
        property_value: Optional[Any],
        context: ProcessingContext
    ) -> Dict:
        """
        Создает условие для проверки предмета
        
        Returns:
            Словарь с условием
        """
        if check_type == 'has':
            return {
                "type": "item_check",
                "item": item_id,
                "check": "has",
                "quantity": quantity
            }
        
        elif check_type == 'has_not':
            return {
                "type": "item_check",
                "item": item_id,
                "check": "has_not",
                "quantity": quantity
            }
        
        elif check_type == 'quantity':
            # Проверка количества предметов
            actual_quantity = self._get_item_quantity(item_id, context)
            return {
                "type": "direct_check",
                "left": actual_quantity,
                "operator": ">=",
                "right": quantity
            }
        
        elif check_type == 'property' and property_name:
            # Проверка свойства предмета
            item = self._get_item(item_id, context)
            if item and property_name in item.properties:
                prop_value = item.properties[property_name]
                return {
                    "type": "direct_check",
                    "left": prop_value,
                    "operator": "==",
                    "right": property_value
                }
        
        return {
            "type": "boolean_check",
            "value": False
        }
    
    def _add_to_inventory(self, item_data: Dict, context: ProcessingContext):
        """Добавляет предмет в текущий инвентарь"""
        item_id = item_data['id']
        quantity = item_data.get('quantity', 1)
        
        if item_id in self.inventory:
            if self.inventory[item_id].stackable:
                self.inventory[item_id].quantity += quantity
            else:
                # Если предмет не стакается, создаем новый экземпляр
                new_item = Item.from_dict(item_data)
                new_item.id = f"{item_id}_{uuid.uuid4().hex[:4]}"
                self.inventory[new_item.id] = new_item
        else:
            self.inventory[item_id] = Item.from_dict(item_data)
        
        # Сохраняем инвентарь в контексте
        if not hasattr(context, 'inventory'):
            context.inventory = {}
        
        context.inventory.update(self.inventory)
    
    def _remove_from_inventory(self, item_id: str, quantity: int, context: ProcessingContext):
        """Удаляет предмет из инвентаря"""
        if item_id in self.inventory:
            if self.inventory[item_id].stackable:
                self.inventory[item_id].quantity -= quantity
                if self.inventory[item_id].quantity <= 0:
                    del self.inventory[item_id]
            else:
                del self.inventory[item_id]
        
        # Обновляем контекст
        if hasattr(context, 'inventory'):
            context.inventory = self.inventory.copy()
    
    def _get_item(self, item_id: str, context: ProcessingContext) -> Optional[Item]:
        """Возвращает предмет по ID"""
        if hasattr(context, 'inventory') and item_id in context.inventory:
            return context.inventory[item_id]
        return self.inventory.get(item_id)
    
    def _get_item_quantity(self, item_id: str, context: ProcessingContext) -> int:
        """Возвращает количество предмета в инвентаре"""
        item = self._get_item(item_id, context)
        return item.quantity if item else 0


# Экспортируем экземпляр процессора
processor = ItemsProcessor()