"""
Models for global variables and flags
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class VariableType(str, Enum):
    """Variable types"""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class VariableOperation(str, Enum):
    """Operations with variables"""
    SET = "set"        # присвоить значение
    ADD = "add"        # добавить (для чисел)
    SUBTRACT = "sub"   # вычесть
    MULTIPLY = "mul"   # умножить
    DIVIDE = "div"     # разделить
    APPEND = "append"  # добавить в конец массива
    REMOVE = "remove"  # удалить из массива


class GlobalFlag(BaseModel):
    """
    Global variable/flag

    Stores the variable's state, type, and metadata.
    Supports both simple values ​​and complex structures.
    """
    name: str = Field(..., description="Имя переменной")
    value: Any = Field(..., description="Текущее значение")
    type: VariableType = Field(..., description="Тип переменной")
    description: Optional[str] = Field(None, description="Описание переменной")
    persistent: bool = Field(True, description="Сохранять между эпизодами?")
    min_value: Optional[float] = Field(None, description="Минимальное значение (для чисел)")
    max_value: Optional[float] = Field(None, description="Максимальное значение (для чисел)")
    
    class Config:
        frozen = False  # можно изменять
        use_enum_values = True
    
    def set_value(self, new_value: Any) -> 'GlobalFlag':
        """Sets a new value with type checking """
        # Checking the type
        new_type = self._infer_type(new_value)
        if new_type != self.type:
            raise ValueError(f"Type mismatch: expected {self.type}, got {new_type}")
        
        # Checking the boundaries for numbers
        if self.type in [VariableType.INTEGER, VariableType.FLOAT]:
            if self.min_value is not None and new_value < self.min_value:
                raise ValueError(f"Value {new_value} is below minimum {self.min_value}")
            if self.max_value is not None and new_value > self.max_value:
                raise ValueError(f"Value {new_value} is above maximum {self.max_value}")
        
        self.value = new_value
        return self
    
    def apply_operation(self, operation: VariableOperation, operand: Any) -> 'GlobalFlag':
        """Applies an operation to a variable"""
        if operation == VariableOperation.SET:
            return self.set_value(operand)
        
        elif operation == VariableOperation.ADD:
            if self.type not in [VariableType.INTEGER, VariableType.FLOAT]:
                raise ValueError(f"Cannot add to {self.type}")
            return self.set_value(self.value + operand)
        
        elif operation == VariableOperation.SUBTRACT:
            if self.type not in [VariableType.INTEGER, VariableType.FLOAT]:
                raise ValueError(f"Cannot subtract from {self.type}")
            return self.set_value(self.value - operand)
        
        elif operation == VariableOperation.MULTIPLY:
            if self.type not in [VariableType.INTEGER, VariableType.FLOAT]:
                raise ValueError(f"Cannot multiply {self.type}")
            return self.set_value(self.value * operand)
        
        elif operation == VariableOperation.DIVIDE:
            if self.type not in [VariableType.INTEGER, VariableType.FLOAT]:
                raise ValueError(f"Cannot divide {self.type}")
            if operand == 0:
                raise ValueError("Division by zero")
            return self.set_value(self.value / operand)
        
        elif operation == VariableOperation.APPEND:
            if self.type != VariableType.ARRAY:
                raise ValueError(f"Cannot append to {self.type}")
            if not isinstance(self.value, list):
                self.value = []
            self.value.append(operand)
            return self
        
        elif operation == VariableOperation.REMOVE:
            if self.type != VariableType.ARRAY:
                raise ValueError(f"Cannot remove from {self.type}")
            if isinstance(self.value, list) and operand in self.value:
                self.value.remove(operand)
            return self
        
        raise ValueError(f"Unknown operation: {operation}")
    
    @staticmethod
    def _infer_type(value: Any) -> VariableType:
        """Defines the value type"""
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
            raise ValueError(f"Cannot infer type for {value}")
    
    def to_dict(self) -> dict:
        """Converts to a dictionary for serialization"""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.type.value,
            "description": self.description,
            "persistent": self.persistent
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GlobalFlag':
        """Creates from the dictionary"""
        return cls(
            name=data["name"],
            value=data["value"],
            type=VariableType(data["type"]),
            description=data.get("description"),
            persistent=data.get("persistent", True)
        )