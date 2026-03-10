"""
Процессор для тегов глобальных переменных: [SET_GLOBAL], [ADD_GLOBAL], [SAVE_GLOBAL]
Управляет состоянием игры
"""

from typing import Optional, Dict, Any, Tuple, List

from ...models.node import Node, Effect
from ...models.flag import GlobalFlag, VariableType, VariableOperation
from ...parsers.tag_parser import TagType, TagParser
from ..tag_processor import TagProcessor, ProcessingContext
from .choice import ChoiceProcessor


class GlobalsProcessor(TagProcessor):
    """
    Обработчик тегов глобальных переменных
    
    Форматы:
    - [SET_GLOBAL] variable = value
    - [SET_GLOBAL] {"name": "variable", "value": value}
    
    - [ADD_GLOBAL] variable = value
    - [ADD_GLOBAL] {"name": "variable", "value": 1}
    
    - [SAVE_GLOBAL] variable
    - [SAVE_GLOBAL] {"name": "variable"}
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        # Ссылка на ChoiceProcessor для добавления эффектов
        self.choice_processor = None
    
    def set_choice_processor(self, choice_processor: ChoiceProcessor):
        """Устанавливает ссылку на ChoiceProcessor"""
        self.choice_processor = choice_processor
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [
            TagType.SET_GLOBAL,
            TagType.ADD_GLOBAL,
            TagType.SAVE_GLOBAL,
            TagType.GET_GLOBAL
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
        
        # Парсим эффект
        effect = TagParser.parse_effect(tag_type, value, params)
        
        if not effect:
            errors.append(f"Failed to parse effect from {tag_type.value}")
            return context.current_node, errors
        
        # Проверяем, находимся ли мы внутри блока выбора
        if self.choice_processor and hasattr(self.choice_processor, 'current_choice'):
            if self.choice_processor.current_choice:
                # Добавляем эффект к текущему выбору
                self.choice_processor.add_effect_to_current_choice(effect)
                self.log_debug(f"Added effect to current choice: {effect}", context)
                return context.current_node, None
        
        # Иначе добавляем как эффект при входе в ноду
        if not hasattr(context.current_node, 'transitions'):
            from ...models.node import Transition
            context.current_node.transitions = Transition()
        
        # Добавляем в on_enter
        if tag_type in [TagType.SET_GLOBAL, TagType.ADD_GLOBAL]:
            context.current_node.transitions.on_enter.append(Effect(**effect))
            self.log_debug(f"Added on_enter effect: {effect}", context)
        
        # Сохраняем переменную в контексте для валидации
        self._track_variable(effect, context)
        
        return context.current_node, errors if errors else None
    
    def _track_variable(self, effect: Dict, context: ProcessingContext):
        """Отслеживает использование переменной для валидации"""
        if 'variable' in effect:
            var_name = effect['variable']
            
            if not hasattr(context, 'used_variables'):
                context.used_variables = set()
            
            context.used_variables.add(var_name)
            
            # Если переменная еще не определена, создаем её с типом по умолчанию
            if var_name not in context.variables:
                value = effect.get('value', 0)
                var_type = self._infer_type(value)
                
                context.variables[var_name] = GlobalFlag(
                    name=var_name,
                    value=value,
                    type=var_type
                )
                self.log_debug(f"Created new variable: ${var_name} = {value}", context)
    
    def _infer_type(self, value: Any) -> VariableType:
        """Определяет тип переменной по значению"""
        if isinstance(value, bool):
            return VariableType.BOOLEAN
        elif isinstance(value, int):
            return VariableType.INTEGER
        elif isinstance(value, float):
            return VariableType.FLOAT
        elif isinstance(value, str):
            return VariableType.STRING
        elif isinstance(value, list):
            return VariableType.ARRAY
        elif isinstance(value, dict):
            return VariableType.OBJECT
        else:
            return VariableType.INTEGER
    
    def get_variable(self, name: str, context: ProcessingContext) -> Optional[GlobalFlag]:
        """Возвращает переменную по имени"""
        return context.variables.get(name)
    
    def set_variable(self, name: str, value: Any, context: ProcessingContext):
        """Устанавливает значение переменной"""
        if name in context.variables:
            context.variables[name].set_value(value)
        else:
            var_type = self._infer_type(value)
            context.variables[name] = GlobalFlag(
                name=name,
                value=value,
                type=var_type
            )


# Экспортируем экземпляр процессора
processor = GlobalsProcessor()