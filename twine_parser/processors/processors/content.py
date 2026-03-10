"""
Процессор для текстового контента: [TEXT] и обычный текст
Создает элементы контента (нарратив, диалоги, действия)
"""

from typing import Optional, Dict, Any, Tuple, List

from ...models.node import ContentItem, ContentType, CharacterEmotion
from ...parsers.tag_parser import TagType, TagParser
from ..tag_processor import TagProcessor, ProcessingContext


class ContentProcessor(TagProcessor):
    """
    Обработчик текстового контента
    
    Форматы:
    - [TEXT] Текст повествования
    - [TEXT] {"text": "...", "type": "narration"}
    - Обычный текст (без тега) - как действие/описание
    """
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [TagType.TEXT, TagType.UNKNOWN]
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        # Определяем тип контента и текст
        content_type = ContentType.NARRATION
        text = None
        emotion = CharacterEmotion.NEUTRAL
        
        if tag_type == TagType.TEXT and params:
            # [TEXT] с параметрами
            text = params.get('text') or params.get('value')
            content_type_str = params.get('type', 'narration')
            emotion_str = params.get('emotion', 'neutral')
            
            # Конвертируем тип
            try:
                content_type = ContentType(content_type_str)
            except ValueError:
                errors.append(f"Invalid content type: {content_type_str}")
            
            # Конвертируем эмоцию
            try:
                emotion = CharacterEmotion(emotion_str)
            except ValueError:
                pass
        
        elif tag_type == TagType.TEXT and value:
            # [TEXT] Простой текст
            text = value.strip()
        
        elif tag_type == TagType.UNKNOWN:
            # Обычный текст без тега - это действие/описание
            text = value if value else ""
            if text and not text.startswith('//'):  # не комментарий
                content_type = ContentType.ACTION
        
        if not text:
            return context.current_node, errors
        
        # Извлекаем ссылки из текста
        links = TagParser.extract_links(text)
        if links:
            self.log_debug(f"Found links in text: {links}", context)
            # Ссылки будут обработаны отдельно
        
        # Проверяем, есть ли ожидающий speaker
        speaker = getattr(context, 'pending_speaker', None)
        
        if speaker:
            # Это диалог
            content_type = ContentType.DIALOGUE
            
            # Создаем элемент диалога
            content_item = ContentItem(
                type=content_type,
                speaker=speaker,
                text=text,
                emotion=emotion
            )
            
            # Сбрасываем pending_speaker
            context.pending_speaker = None
            
            self.log_debug(f"Added dialogue from {speaker}: {text[:50]}...", context)
        
        else:
            # Это нарратив или действие
            content_item = ContentItem(
                type=content_type,
                text=text if content_type != ContentType.ACTION else None,
                description=text if content_type == ContentType.ACTION else None
            )
            
            self.log_debug(f"Added {content_type.value}: {text[:50]}...", context)
        
        # Добавляем в ноду
        context.current_node.add_content(content_item)
        
        return context.current_node, errors if errors else None


# Экспортируем экземпляр процессора
processor = ContentProcessor()