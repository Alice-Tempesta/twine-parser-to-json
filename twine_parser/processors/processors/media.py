"""
Процессор для медиа-тегов: [BG], [MUSIC], [SOUND]
Управляет фонами, музыкой и звуками
"""

from typing import Optional, Dict, Any, Tuple, List

from ...models.node import MediaAsset
from ...parsers.tag_parser import TagType
from ..tag_processor import TagProcessor, ProcessingContext


class MediaProcessor(TagProcessor):
    """
    Обработчик медиа-тегов
    
    Форматы:
    - [BG] background.jpg
    - [BG] {"file": "bg.jpg", "fade": true}
    
    - [MUSIC] music.mp3
    - [MUSIC] {"file": "music.mp3", "loop": true, "volume": 0.7}
    
    - [SOUND] sound.mp3
    - [SOUND] {"file": "sound.mp3", "loop": false, "volume": 1.0}
    """
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [TagType.BG, TagType.MUSIC, TagType.SOUND]
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        if tag_type == TagType.BG:
            return self._process_background(value, params, context, errors)
        elif tag_type == TagType.MUSIC:
            return self._process_music(value, params, context, errors)
        elif tag_type == TagType.SOUND:
            return self._process_sound(value, params, context, errors)
        
        return context.current_node, errors
    
    def _process_background(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [BG] тег"""
        
        bg_file = None
        fade = False
        
        if params:
            bg_file = params.get('file') or params.get('bg')
            fade = params.get('fade', False)
        elif value:
            bg_file = value.strip()
        
        if not bg_file:
            errors.append("Background file is required")
            return context.current_node, errors
        
        # Устанавливаем фон
        context.current_node.set_background(bg_file)
        
        # Добавляем параметры если есть
        if fade:
            # Можно добавить в transitions или media параметры
            if 'params' not in context.current_node.media:
                context.current_node.media['params'] = {}
            context.current_node.media['params']['fade'] = fade
        
        self.log_debug(f"Set background: {bg_file}", context)
        
        return context.current_node, errors if errors else None
    
    def _process_music(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [MUSIC] тег"""
        
        music_file = None
        loop = True
        volume = 1.0
        
        if params:
            music_file = params.get('file') or params.get('music')
            loop = params.get('loop', True)
            volume = float(params.get('volume', 1.0))
        elif value:
            music_file = value.strip()
        
        if not music_file:
            errors.append("Music file is required")
            return context.current_node, errors
        
        # Устанавливаем музыку
        context.current_node.set_music(music_file)
        
        # Добавляем параметры
        music_params = {
            'loop': loop,
            'volume': volume
        }
        
        if 'params' not in context.current_node.media:
            context.current_node.media['params'] = {}
        context.current_node.media['params']['music'] = music_params
        
        self.log_debug(f"Set music: {music_file} (loop={loop}, volume={volume})", context)
        
        return context.current_node, errors if errors else None
    
    def _process_sound(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [SOUND] тег"""
        
        sound_file = None
        loop = False
        volume = 1.0
        
        if params:
            sound_file = params.get('file') or params.get('sound')
            loop = params.get('loop', False)
            volume = float(params.get('volume', 1.0))
        elif value:
            sound_file = value.strip()
        
        if not sound_file:
            errors.append("Sound file is required")
            return context.current_node, errors
        
        # Создаем звуковой ассет
        sound = MediaAsset(
            file=sound_file,
            loop=loop,
            volume=volume
        )
        
        # Добавляем звук
        context.current_node.add_sound(sound)
        
        self.log_debug(f"Added sound: {sound_file}", context)
        
        return context.current_node, errors if errors else None


# Экспортируем экземпляр процессора
processor = MediaProcessor()