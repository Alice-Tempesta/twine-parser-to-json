"""
Базовый класс для всех процессоров тегов
Определяет интерфейс обработки тегов
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from ..models.node import Node
from ..parsers.tag_parser import TagType


@dataclass
class ProcessingContext:
    """Контекст обработки"""
    current_node: Node
    current_episode_num: int
    all_nodes: Dict[str, Node]
    variables: Dict[str, Any]
    debug: bool = False
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Получает ноду по ID"""
        return self.all_nodes.get(node_id)


class TagProcessor(ABC):
    """
    Базовый класс для обработчиков тегов
    
    Каждый конкретный процессор должен реализовать:
    - can_process: проверяет, может ли обработать тег
    - process: обрабатывает тег
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
    
    @abstractmethod
    def can_process(self, tag_type: TagType) -> bool:
        """
        Проверяет, может ли этот процессор обработать тег
        
        Args:
            tag_type: Тип тега
            
        Returns:
            True если может обработать
        """
        pass
    
    @abstractmethod
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        """
        Обрабатывает тег
        
        Args:
            tag_type: Тип тега
            value: Значение тега
            params: Параметры тега
            context: Контекст обработки
            line_number: Номер строки в исходном файле
            
        Returns:
            Кортеж (обновленная нода, список ошибок)
        """
        pass
    
    def validate_value(self, value: Optional[str], required: bool = False) -> Optional[str]:
        """Checks for the presence of a value"""
        if required and not value:
            return "Missing required value"
        return None
    
    def log_debug(self, message: str, context: ProcessingContext):
        """Logs a debug message"""
        if context.debug:
            print(f"[DEBUG] {message}")