"""
Процессор для условных тегов: [IF], [IF_NOT], [AND], [OR]
Обрабатывает условия для ветвления сюжета
"""

from typing import Optional, Dict, Any, Tuple, List
import re

from ...models.node import Node, Condition
from ...parsers.tag_parser import TagType, TagParser
from ..tag_processor import TagProcessor, ProcessingContext


class ConditionsProcessor(TagProcessor):
    """
    Обработчик условных тегов
    
    Форматы:
    - [IF] variable == value
    - [IF] {"condition": "variable == value", "then": "node_id", "else": "node_id"}
    - [IF_NOT] variable == value
    - [AND] variable == value
    - [OR] variable == value
    
    Поддерживаемые операторы:
    - ==, !=, >, <, >=, <=
    - contains, in
    - is, is not
    """
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [
            TagType.IF, 
            TagType.IF_NOT, 
            TagType.AND, 
            TagType.OR
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
        
        if tag_type == TagType.IF:
            return self._process_if(value, params, context, errors)
        elif tag_type == TagType.IF_NOT:
            return self._process_if_not(value, params, context, errors)
        elif tag_type in [TagType.AND, TagType.OR]:
            return self._process_logical(tag_type, value, params, context, errors)
        
        return context.current_node, errors
    
    def _process_if(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [IF] тег"""
        
        condition_str = None
        then_node = None
        else_node = None
        
        if params:
            # Формат с параметрами
            condition_str = params.get('condition') or params.get('if')
            then_node = params.get('then')
            else_node = params.get('else')
        elif value:
            # Простой формат: [IF] condition
            condition_str = value.strip()
        
        if not condition_str:
            errors.append("IF condition is required")
            return context.current_node, errors
        
        # Парсим условие
        condition = TagParser.parse_condition(condition_str)
        
        # Если есть then/else, создаем условный переход
        if then_node:
            context.current_node.condition = Condition(
                type="if",
                condition=condition_str,
                then=then_node,
                else_=else_node
            )
            self.log_debug(f"Set conditional: if {condition_str} -> {then_node}", context)
        else:
            # Просто сохраняем условие в контексте для следующих элементов
            if not hasattr(context, 'conditions_stack'):
                context.conditions_stack = []
            context.conditions_stack.append({
                'type': 'if',
                'condition': condition,
                'raw': condition_str,
                'active': None  # будет вычислено позже
            })
            self.log_debug(f"Pushed condition: {condition_str}", context)
        
        return context.current_node, errors if errors else None
    
    def _process_if_not(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [IF_NOT] тег"""
        
        condition_str = None
        
        if params:
            condition_str = params.get('condition') or params.get('if_not')
        elif value:
            condition_str = value.strip()
        
        if not condition_str:
            errors.append("IF_NOT condition is required")
            return context.current_node, errors
        
        # Инвертируем условие добавляя NOT
        condition_str = f"not ({condition_str})"
        
        # Добавляем в стек условий
        if not hasattr(context, 'conditions_stack'):
            context.conditions_stack = []
        
        context.conditions_stack.append({
            'type': 'if_not',
            'condition': TagParser.parse_condition(condition_str),
            'raw': condition_str,
            'active': None
        })
        
        self.log_debug(f"Pushed inverted condition: {condition_str}", context)
        
        return context.current_node, errors if errors else None
    
    def _process_logical(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [AND] и [OR] теги"""
        
        condition_str = None
        
        if params:
            condition_str = params.get('condition')
        elif value:
            condition_str = value.strip()
        
        if not condition_str:
            errors.append(f"{tag_type.value.upper()} condition is required")
            return context.current_node, errors
        
        # Добавляем в стек условий с логическим оператором
        if not hasattr(context, 'conditions_stack'):
            context.conditions_stack = []
        
        context.conditions_stack.append({
            'type': tag_type.value.lower(),
            'condition': TagParser.parse_condition(condition_str),
            'raw': condition_str,
            'active': None
        })
        
        self.log_debug(f"Pushed {tag_type.value} condition: {condition_str}", context)
        
        return context.current_node, errors if errors else None
    
    def evaluate_conditions(self, context: ProcessingContext, variables: Dict) -> bool:
        """
        Вычисляет все условия в стеке
        
        Args:
            context: Контекст обработки
            variables: Текущие значения переменных
            
        Returns:
            True если все условия выполняются, иначе False
        """
        if not hasattr(context, 'conditions_stack') or not context.conditions_stack:
            return True
        
        result = True
        current_logical = 'and'  # по умолчанию AND между условиями
        
        for cond in context.conditions_stack:
            cond_result = self._evaluate_single_condition(cond['condition'], variables)
            cond['active'] = cond_result
            
            if current_logical == 'and':
                result = result and cond_result
            else:  # 'or'
                result = result or cond_result
            
            # Следующий логический оператор (если есть)
            if cond.get('type') in ['and', 'or']:
                current_logical = cond['type']
        
        return result
    
    def _evaluate_single_condition(self, condition: Dict, variables: Dict) -> bool:
        """
        Вычисляет одно условие
        
        Args:
            condition: Распарсенное условие
            variables: Переменные
            
        Returns:
            Результат условия
        """
        if condition['type'] == 'boolean_check':
            return bool(condition['value'])
        
        elif condition['type'] == 'direct_check':
            left = condition['left']
            right = condition['right']
            op = condition['operator']
            return self._compare(left, right, op)
        
        elif condition['type'] == 'variable_check':
            var_name = condition['variable']
            var_value = variables.get(var_name, 0)
            right = condition['value']
            op = condition['operator']
            return self._compare(var_value, right, op)
        
        return False
    
    def _compare(self, left: Any, right: Any, operator: str) -> bool:
        """Сравнивает два значения"""
        
        if operator in ['eq', '==', 'is']:
            return left == right
        elif operator in ['ne', '!=', 'is_not']:
            return left != right
        elif operator in ['gt', '>']:
            return left > right
        elif operator in ['lt', '<']:
            return left < right
        elif operator in ['ge', '>=']:
            return left >= right
        elif operator in ['le', '<=']:
            return left <= right
        elif operator == 'contains':
            return right in left if hasattr(left, '__contains__') else False
        elif operator == 'in':
            return left in right if hasattr(right, '__contains__') else False
        
        return False
    
    def clear_conditions(self, context: ProcessingContext):
        """Очищает стек условий"""
        if hasattr(context, 'conditions_stack'):
            delattr(context, 'conditions_stack')


# Экспортируем экземпляр процессора
processor = ConditionsProcessor()