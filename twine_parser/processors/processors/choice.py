"""
Процессор для тегов выбора: [CHOICE] и [OPTION]
Создает варианты выбора для интерактивных диалогов
"""

from typing import Optional, Dict, Any, Tuple, List
import uuid

from ...models.node import Node, Choice, Effect
from ...parsers.tag_parser import TagType, TagParser
from ..tag_processor import TagProcessor, ProcessingContext


class ChoiceProcessor(TagProcessor):
    """
    Обработчик тегов выбора
    
    Форматы:
    - [CHOICE] (открывает блок выбора)
    - [OPTION] Текст выбора
    - [OPTION] {"text": "Текст", "goto": "node_id", "condition": "..."}
    
    Внутри OPTION могут быть:
    - [ADD_GLOBAL] intelligence = 1
    - [GIVE_ITEM] item_name
    - [COST] energy = 10
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.in_choice_block = False
        self.current_choice = None
        self.current_choice_effects = []
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [TagType.CHOICE, TagType.OPTION]
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        if tag_type == TagType.CHOICE:
            return self._process_choice_start(value, params, context, errors)
        elif tag_type == TagType.OPTION:
            return self._process_option(value, params, context, errors)
        
        return context.current_node, errors
    
    def _process_choice_start(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """
        Обрабатывает начало блока выбора [CHOICE]
        """
        self.in_choice_block = True
        self.current_choice = None
        self.current_choice_effects = []
        
        self.log_debug("Started choice block", context)
        
        return context.current_node, None
    
    def _process_option(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """
        Обрабатывает опцию выбора [OPTION]
        """
        if not self.in_choice_block:
            errors.append("[OPTION] found outside of [CHOICE] block")
            return context.current_node, errors
        
        # Если есть предыдущий choice, сохраняем его
        if self.current_choice:
            self._save_current_choice(context, errors)
        
        # Парсим текущую опцию
        choice_text = None
        choice_id = f"choice_{uuid.uuid4().hex[:8]}"
        choice_goto = None
        choice_condition = None
        choice_enabled = True
        choice_visible = True
        
        if params:
            # Формат с параметрами
            choice_text = params.get('text') or params.get('value')
            choice_id = params.get('id', choice_id)
            choice_goto = params.get('goto')
            choice_condition = params.get('condition')
            choice_enabled = params.get('enabled', True)
            choice_visible = params.get('visible', True)
        elif value:
            # Простой формат: [OPTION] Текст выбора
            # Текст может содержать ссылку в конце: Текст выбора [[node_id]]
            choice_text, choice_goto = self._extract_goto_from_text(value)
        
        if not choice_text:
            errors.append("Choice text is required")
            return context.current_node, errors
        
        # Создаем объект выбора
        self.current_choice = Choice(
            id=choice_id,
            text=choice_text,
            enabled=choice_enabled,
            visible=choice_visible,
            effects=[],  # будут добавлены позже
            goto=choice_goto,
            condition=choice_condition
        )
        
        self.log_debug(f"Created choice option: {choice_text[:30]}...", context)
        
        return context.current_node, errors if errors else None
    
    def _extract_goto_from_text(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Извлекает ссылку [[node_id]] из текста опции
        
        Args:
            text: Текст опции
            
        Returns:
            Кортеж (текст_без_ссылки, целевая_нода)
        """
        links = TagParser.extract_links(text)
        if links:
            # Берем первую ссылку
            target = links[0]
            # Убираем ссылку из текста
            clean_text = TagParser.replace_links(text, "").strip()
            return clean_text, target
        
        return text, None
    
    def _save_current_choice(self, context: ProcessingContext, errors: List[str]):
        """
        Сохраняет текущий choice в ноду
        """
        if not self.current_choice:
            return
        
        # Добавляем эффекты
        self.current_choice.effects = self.current_choice_effects.copy()
        
        # Добавляем choice в ноду
        context.current_node.add_choice(self.current_choice)
        
        self.log_debug(f"Saved choice: {self.current_choice.id}", context)
        
        # Сбрасываем для следующей опции
        self.current_choice = None
        self.current_choice_effects = []
    
    def add_effect_to_current_choice(self, effect: Dict):
        """
        Добавляет эффект к текущему choice (вызывается из других процессоров)
        """
        if self.current_choice:
            self.current_choice_effects.append(effect)
    
    def end_choice_block(self, context: ProcessingContext):
        """
        Завершает блок выбора (вызывается в конце обработки ноды)
        """
        if self.in_choice_block and self.current_choice:
            self._save_current_choice(context, [])
        
        self.in_choice_block = False
        self.current_choice = None
        self.current_choice_effects = []


# Экспортируем экземпляр процессора
processor = ChoiceProcessor()