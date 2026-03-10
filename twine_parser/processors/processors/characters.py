"""
Процессор для тегов персонажей: [CHAR], [HIDE_CHAR], [SPEAKER]
Управляет персонажами на сцене
"""

from typing import Optional, Dict, Any, Tuple, List

from ...models.node import CharacterOnScene, CharacterPosition, CharacterEmotion
from ...parsers.tag_parser import TagType
from ..tag_processor import TagProcessor, ProcessingContext


class CharacterProcessor(TagProcessor):
    """
    Обработчик тегов персонажей
    
    Форматы:
    - [CHAR] character_sprite
    - [CHAR] {"id": "leila", "sprite": "leila_normal", "position": "center"}
    
    - [HIDE_CHAR] character_id
    
    - [SPEAKER] character_id
    """
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [TagType.CHAR, TagType.HIDE_CHAR, TagType.SPEAKER]
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        if tag_type == TagType.CHAR:
            return self._process_char(value, params, context, errors)
        elif tag_type == TagType.HIDE_CHAR:
            return self._process_hide_char(value, params, context, errors)
        elif tag_type == TagType.SPEAKER:
            return self._process_speaker(value, params, context, errors)
        
        return context.current_node, errors
    
    def _process_char(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [CHAR] тег - добавление персонажа на сцену"""
        
        char_id = None
        sprite = None
        position = CharacterPosition.CENTER
        emotion = CharacterEmotion.NEUTRAL
        flip = False
        
        if params:
            # Формат с параметрами
            char_id = params.get('id') or params.get('char')
            sprite = params.get('sprite') or params.get('char')
            position_str = params.get('position', 'center')
            emotion_str = params.get('emotion', 'neutral')
            flip = params.get('flip', False)
            
            # Конвертируем позицию
            try:
                position = CharacterPosition(position_str)
            except ValueError:
                errors.append(f"Invalid position: {position_str}")
            
            # Конвертируем эмоцию
            try:
                emotion = CharacterEmotion(emotion_str)
            except ValueError:
                errors.append(f"Invalid emotion: {emotion_str}")
        
        elif value:
            # Простой формат: [CHAR] sprite_name
            # В этом случае ID = sprite_name
            char_id = value.strip()
            sprite = value.strip()
        
        if not char_id:
            errors.append("Character ID is required")
            return context.current_node, errors
        
        if not sprite:
            sprite = char_id
        
        # Создаем персонажа
        character = CharacterOnScene(
            id=char_id,
            sprite=sprite,
            position=position,
            emotion=emotion,
            flip=flip
        )
        
        # Добавляем на сцену
        context.current_node.add_character(character)
        
        self.log_debug(f"Added character: {char_id} ({sprite}) at {position.value}", context)
        
        return context.current_node, errors if errors else None
    
    def _process_hide_char(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [HIDE_CHAR] тег - убирает персонажа со сцены"""
        
        char_id = None
        
        if params:
            char_id = params.get('id') or params.get('char')
        elif value:
            char_id = value.strip()
        
        if not char_id:
            errors.append("Character ID is required for HIDE_CHAR")
            return context.current_node, errors
        
        # Убираем персонажа
        context.current_node.remove_character(char_id)
        
        self.log_debug(f"Removed character: {char_id}", context)
        
        return context.current_node, errors if errors else None
    
    def _process_speaker(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [SPEAKER] тег - устанавливает говорящего для следующей реплики"""
        
        speaker_id = None
        
        if params:
            speaker_id = params.get('id') or params.get('speaker')
        elif value:
            speaker_id = value.strip()
        
        if not speaker_id:
            errors.append("Speaker ID is required")
            return context.current_node, errors
        
        # Сохраняем speaker в контексте для следующего [TEXT]
        # Это будет обработано в ContentProcessor
        if not hasattr(context, 'pending_speaker'):
            context.pending_speaker = speaker_id
        
        self.log_debug(f"Set pending speaker: {speaker_id}", context)
        
        return context.current_node, errors if errors else None


# Экспортируем экземпляр процессора
processor = CharacterProcessor()