"""
Процессор для кастомных виджетов: [CUSTOM_WIDGET], [PARAMS]
Позволяет создавать переиспользуемые компоненты
"""

from typing import Optional, Dict, Any, Tuple, List
import json
import uuid

from ...models.node import Node, ContentItem, ContentType
from ...parsers.tag_parser import TagType, TagParser
from ..tag_processor import TagProcessor, ProcessingContext


class CustomWidget:
    """
    Класс для представления кастомного виджета
    """
    def __init__(self, widget_id: str, name: str, template: str, 
                 params_schema: Dict = None, description: str = ""):
        self.id = widget_id
        self.name = name
        self.template = template
        self.params_schema = params_schema or {}
        self.description = description
        self.instances = []
    
    def render(self, params: Dict, instance_id: str) -> str:
        """
        Рендерит виджет с заданными параметрами
        
        Args:
            params: Параметры для подстановки
            instance_id: ID экземпляра
            
        Returns:
            Отрендеренный HTML/текст
        """
        rendered = self.template
        
        # Простая подстановка параметров вида {{param_name}}
        for key, value in params.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        
        return rendered
    
    def validate_params(self, params: Dict) -> List[str]:
        """
        Проверяет переданные параметры
        
        Args:
            params: Параметры для проверки
            
        Returns:
            Список ошибок
        """
        errors = []
        
        for param_name, param_config in self.params_schema.items():
            param_type = param_config.get('type', 'string')
            required = param_config.get('required', False)
            
            if required and param_name not in params:
                errors.append(f"Required parameter '{param_name}' is missing")
                continue
            
            if param_name in params:
                value = params[param_name]
                
                # Проверка типа
                if param_type == 'string' and not isinstance(value, str):
                    errors.append(f"Parameter '{param_name}' should be string, got {type(value).__name__}")
                elif param_type == 'number' and not isinstance(value, (int, float)):
                    errors.append(f"Parameter '{param_name}' should be number, got {type(value).__name__}")
                elif param_type == 'boolean' and not isinstance(value, bool):
                    errors.append(f"Parameter '{param_name}' should be boolean, got {type(value).__name__}")
                elif param_type == 'array' and not isinstance(value, list):
                    errors.append(f"Parameter '{param_name}' should be array, got {type(value).__name__}")
                elif param_type == 'object' and not isinstance(value, dict):
                    errors.append(f"Parameter '{param_name}' should be object, got {type(value).__name__}")
                
                # Проверка допустимых значений
                if 'enum' in param_config and value not in param_config['enum']:
                    allowed = ', '.join(str(v) for v in param_config['enum'])
                    errors.append(f"Parameter '{param_name}' value '{value}' is not allowed. Allowed: {allowed}")
        
        return errors
    
    def to_dict(self) -> Dict:
        """Конвертирует в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'template': self.template,
            'params_schema': self.params_schema,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CustomWidget':
        """Создает из словаря"""
        return cls(
            widget_id=data['id'],
            name=data['name'],
            template=data['template'],
            params_schema=data.get('params_schema', {}),
            description=data.get('description', '')
        )


class CustomWidgetInstance:
    """
    Экземпляр кастомного виджета в конкретной ноде
    """
    def __init__(self, widget_id: str, instance_id: str, params: Dict):
        self.widget_id = widget_id
        self.instance_id = instance_id
        self.params = params
        self.rendered_content = None
    
    def to_dict(self) -> Dict:
        """Конвертирует в словарь"""
        return {
            'widget_id': self.widget_id,
            'instance_id': self.instance_id,
            'params': self.params
        }


class CustomProcessor(TagProcessor):
    """
    Обработчик кастомных виджетов
    
    Форматы:
    - [CUSTOM_WIDGET] widget_name
    - [CUSTOM_WIDGET] {"name": "button", "template": "<button>{{text}}</button>", 
                        "params": {"text": {"type": "string", "required": true}}}
    
    - [PARAMS] {"text": "Click me", "color": "red"}
    
    Виджеты могут быть определены один раз и использоваться многократно
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.widgets = {}  # {widget_id: CustomWidget}
        self.current_widget_definition = None
        self.current_widget_instance = None
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [TagType.CUSTOM_WIDGET, TagType.PARAMS]
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        if tag_type == TagType.CUSTOM_WIDGET:
            return self._process_custom_widget(value, params, context, errors)
        elif tag_type == TagType.PARAMS:
            return self._process_params(value, params, context, errors)
        
        return context.current_node, errors
    
    def _process_custom_widget(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """
        Обрабатывает [CUSTOM_WIDGET] тег
        
        Может быть двух типов:
        1. Определение нового виджета
        2. Использование существующего виджета
        """
        
        if params and ('template' in params or 'widget' in params):
            # Определение нового виджета
            return self._define_widget(value, params, context, errors)
        else:
            # Использование существующего виджета
            return self._use_widget(value, params, context, errors)
    
    def _define_widget(
        self,
        value: Optional[str],
        params: Dict,
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Определяет новый кастомный виджет"""
        
        widget_name = params.get('name') or value
        widget_id = params.get('id', f"widget_{uuid.uuid4().hex[:8]}")
        template = params.get('template', '')
        description = params.get('description', '')
        params_schema = params.get('params', {})
        
        if not widget_name:
            errors.append("Widget name is required")
            return context.current_node, errors
        
        if not template:
            errors.append("Widget template is required")
            return context.current_node, errors
        
        # Создаем виджет
        widget = CustomWidget(
            widget_id=widget_id,
            name=widget_name,
            template=template,
            params_schema=params_schema,
            description=description
        )
        
        # Сохраняем в реестре
        self.widgets[widget_id] = widget
        self.widgets[widget_name] = widget  # можно обращаться и по имени
        
        self.log_debug(f"Defined custom widget: {widget_name} (id: {widget_id})", context)
        
        return context.current_node, errors if errors else None
    
    def _use_widget(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Использует существующий виджет"""
        
        widget_identifier = value or (params.get('widget') if params else None)
        
        if not widget_identifier:
            errors.append("Widget identifier is required")
            return context.current_node, errors
        
        # Ищем виджет
        widget = self.widgets.get(widget_identifier)
        if not widget:
            # Пробуем найти по имени (case-insensitive)
            for w in self.widgets.values():
                if w.name.lower() == widget_identifier.lower():
                    widget = w
                    break
        
        if not widget:
            errors.append(f"Widget '{widget_identifier}' not found")
            return context.current_node, errors
        
        # Получаем параметры для этого экземпляра
        widget_params = params.get('params', {}) if params else {}
        
        # Проверяем параметры
        param_errors = widget.validate_params(widget_params)
        errors.extend(param_errors)
        
        if errors:
            return context.current_node, errors
        
        # Создаем экземпляр
        instance_id = f"{widget.id}_{uuid.uuid4().hex[:4]}"
        instance = CustomWidgetInstance(
            widget_id=widget.id,
            instance_id=instance_id,
            params=widget_params
        )
        
        # Рендерим содержимое
        rendered = widget.render(widget_params, instance_id)
        
        # Добавляем в контент ноды как специальный тип
        content_item = ContentItem(
            type=ContentType.CUSTOM,
            text=rendered,
            description=f"Widget: {widget.name}"
        )
        
        context.current_node.add_content(content_item)
        
        # Сохраняем информацию о виджете в ноде
        if not hasattr(context.current_node, 'widgets'):
            context.current_node.widgets = []
        
        if not hasattr(context.current_node, 'widget_instances'):
            context.current_node.widget_instances = {}
        
        context.current_node.widgets.append(widget.id)
        context.current_node.widget_instances[instance_id] = instance.to_dict()
        
        self.log_debug(f"Used widget: {widget.name} (instance: {instance_id})", context)
        
        return context.current_node, errors if errors else None
    
    def _process_params(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """
        Обрабатывает [PARAMS] тег - параметры для следующего виджета или события
        
        Форматы:
        - [PARAMS] {"key": "value"}
        - [PARAMS] key = value
        """
        
        parsed_params = {}
        
        if params:
            # Уже распарсенные параметры
            parsed_params = params
        elif value:
            # Пробуем распарсить как JSON
            if value.strip().startswith('{'):
                try:
                    parsed_params = json.loads(value)
                except json.JSONDecodeError:
                    errors.append(f"Failed to parse PARAMS as JSON: {value}")
            else:
                # Пробуем распарсить как key=value пары
                for part in value.split(','):
                    if '=' in part:
                        k, v = part.split('=', 1)
                        parsed_params[k.strip()] = TagParser._parse_value(v.strip())
        
        # Сохраняем параметры в контексте для следующего виджета
        context.current_params = parsed_params
        
        self.log_debug(f"Set params: {parsed_params}", context)
        
        return context.current_node, errors if errors else None
    
    def get_widget(self, identifier: str) -> Optional[CustomWidget]:
        """Возвращает виджет по ID или имени"""
        return self.widgets.get(identifier)
    
    def get_all_widgets(self) -> List[CustomWidget]:
        """Возвращает все определенные виджеты"""
        return list(set(self.widgets.values()))  # уникальные
    
    def clear_widgets(self):
        """Очищает реестр виджетов"""
        self.widgets.clear()


# Экспортируем экземпляр процессора
processor = CustomProcessor()