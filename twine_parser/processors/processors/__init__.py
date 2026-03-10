"""
Конкретные обработчики тегов
Полная версия со всеми процессорами
"""

from .node import processor as node_processor
from .title import processor as title_processor
from .goto import processor as goto_processor
from .media import processor as media_processor
from .characters import processor as characters_processor
from .content import processor as content_processor
from .choice import processor as choice_processor
from .conditions import processor as conditions_processor
from .globals import processor as globals_processor
from .items import processor as items_processor
from .monetization import processor as monetization_processor
from .custom import processor as custom_processor
from .debug import processor as debug_processor

# Устанавливаем связи между процессорами
globals_processor.set_choice_processor(choice_processor)
items_processor.set_choice_processor(choice_processor)
items_processor.set_conditions_processor(conditions_processor)
monetization_processor.set_choice_processor(choice_processor)
monetization_processor.set_conditions_processor(conditions_processor)

# Словарь всех процессоров для удобного доступа
ALL_PROCESSORS = [
    node_processor,
    title_processor,
    goto_processor,
    media_processor,
    characters_processor,
    content_processor,
    choice_processor,
    conditions_processor,
    globals_processor,
    items_processor,
    monetization_processor,
    custom_processor,
    debug_processor,
]

# Маппинг тегов на процессоры
PROCESSOR_MAP = {}

from ...parsers.tag_parser import TagType

for processor in ALL_PROCESSORS:
    for tag_type in TagType:
        if processor.can_process(tag_type):
            if tag_type not in PROCESSOR_MAP:
                PROCESSOR_MAP[tag_type] = []
            PROCESSOR_MAP[tag_type].append(processor)

__all__ = [
    'ALL_PROCESSORS',
    'PROCESSOR_MAP',
    'node_processor',
    'title_processor',
    'goto_processor',
    'media_processor',
    'characters_processor',
    'content_processor',
    'choice_processor',
    'conditions_processor',
    'globals_processor',
    'items_processor',
    'monetization_processor',
    'custom_processor',
    'debug_processor',
]