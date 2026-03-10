"""
Процессор для тегов монетизации: [COST], [REQUIRE_ENERGY]
Управляет внутриигровой валютой и энергией
"""

from typing import Optional, Dict, Any, Tuple, List

from ...models.node import Node, Effect
from ...parsers.tag_parser import TagType, TagParser
from ..tag_processor import TagProcessor, ProcessingContext
from .choice import ChoiceProcessor
from .conditions import ConditionsProcessor


class MonetizationProcessor(TagProcessor):
    """
    Обработчик тегов монетизации
    
    Типы валют:
    - soft_currency - мягкая валюта (монеты, опыт)
    - hard_currency - жесткая валюта (донат)
    - energy - энергия/действия
    - reputation - репутация
    
    Форматы:
    - [COST] currency = amount
    - [COST] {"currency": "soft", "amount": 10, "condition": "has"}
    
    - [REQUIRE_ENERGY] amount
    - [REQUIRE_ENERGY] {"amount": 5, "message": "Не хватает энергии"}
    """
    
    # Типы валют
    CURRENCY_TYPES = {
        'soft': 'soft_currency',
        'soft_currency': 'soft_currency',
        'hard': 'hard_currency',
        'hard_currency': 'hard_currency',
        'energy': 'energy',
        'rep': 'reputation',
        'reputation': 'reputation',
        'gold': 'soft_currency',
        'coins': 'soft_currency',
        'diamonds': 'hard_currency'
    }
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.choice_processor = None
        self.conditions_processor = None
        
        # Начальные значения валют
        self.currencies = {
            'soft_currency': 100,
            'hard_currency': 0,
            'energy': 10,
            'energy_max': 20,
            'reputation': 0
        }
    
    def set_choice_processor(self, choice_processor: ChoiceProcessor):
        """Устанавливает ссылку на ChoiceProcessor"""
        self.choice_processor = choice_processor
    
    def set_conditions_processor(self, conditions_processor: ConditionsProcessor):
        """Устанавливает ссылку на ConditionsProcessor"""
        self.conditions_processor = conditions_processor
    
    def can_process(self, tag_type: TagType) -> bool:
        return tag_type in [TagType.COST, TagType.REQUIRE_ENERGY]
    
    def process(
        self,
        tag_type: TagType,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        line_number: int
    ) -> Tuple[Node, Optional[List[str]]]:
        errors = []
        
        if tag_type == TagType.COST:
            return self._process_cost(value, params, context, errors)
        elif tag_type == TagType.REQUIRE_ENERGY:
            return self._process_require_energy(value, params, context, errors)
        
        return context.current_node, errors
    
    def _process_cost(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [COST] тег - списание валюты"""
        
        currency = 'soft_currency'
        amount = 0
        condition_type = 'has'  # has, has_not, check
        
        if params:
            currency_raw = params.get('currency', 'soft')
            currency = self.CURRENCY_TYPES.get(currency_raw, 'soft_currency')
            amount = int(params.get('amount', 0))
            condition_type = params.get('condition', 'has')
        elif value:
            # Формат: [COST] currency = amount
            parts = value.split('=')
            if len(parts) == 2:
                currency_raw = parts[0].strip()
                currency = self.CURRENCY_TYPES.get(currency_raw, 'soft_currency')
                amount = int(parts[1].strip())
        
        if amount <= 0:
            errors.append("Cost amount must be positive")
            return context.current_node, errors
        
        if condition_type == 'has' or condition_type == 'check':
            # Проверяем, хватает ли валюты
            has_enough = self._check_currency(currency, amount, context)
            
            if condition_type == 'check':
                # Просто проверка - создаем условие
                if self.conditions_processor:
                    condition = {
                        "type": "direct_check",
                        "left": self.currencies.get(currency, 0),
                        "operator": ">=",
                        "right": amount
                    }
                    
                    if not hasattr(context, 'conditions_stack'):
                        context.conditions_stack = []
                    
                    context.conditions_stack.append({
                        'type': 'if',
                        'condition': condition,
                        'raw': f"check_cost: {currency} >= {amount}",
                        'active': None
                    })
                    
                    self.log_debug(f"Added cost check condition: {currency} >= {amount}", context)
                
                return context.current_node, None
            
            elif not has_enough:
                # Не хватает - блокируем выбор
                self.log_debug(f"Not enough {currency} (need {amount})", context)
                
                # Можно добавить сообщение об ошибке
                return context.current_node, None
        
        # Создаем эффект списания
        effect = {
            "type": "cost",
            "currency": currency,
            "amount": amount
        }
        
        # Проверяем, находимся ли мы внутри блока выбора
        if self.choice_processor and hasattr(self.choice_processor, 'current_choice'):
            if self.choice_processor.current_choice:
                # Добавляем эффект к текущему выбору
                self.choice_processor.add_effect_to_current_choice(effect)
                self.log_debug(f"Added cost effect to current choice: {currency} -{amount}", context)
                return context.current_node, None
        
        # Иначе добавляем как эффект при входе в ноду
        if not hasattr(context.current_node, 'transitions'):
            from ...models.node import Transition
            context.current_node.transitions = Transition()
        
        context.current_node.transitions.on_enter.append(Effect(**effect))
        
        # Обновляем текущие значения
        self._spend_currency(currency, amount, context)
        
        self.log_debug(f"Added cost effect: {currency} -{amount}", context)
        
        return context.current_node, errors if errors else None
    
    def _process_require_energy(
        self,
        value: Optional[str],
        params: Optional[Dict],
        context: ProcessingContext,
        errors: List[str]
    ) -> Tuple[Node, Optional[List[str]]]:
        """Обрабатывает [REQUIRE_ENERGY] тег - требование энергии"""
        
        amount = 1
        message = "Недостаточно энергии"
        
        if params:
            amount = int(params.get('amount', 1))
            message = params.get('message', message)
        elif value:
            amount = int(value.strip())
        
        if amount <= 0:
            errors.append("Energy amount must be positive")
            return context.current_node, errors
        
        # Проверяем, хватает ли энергии
        if self.currencies['energy'] < amount:
            self.log_debug(f"Not enough energy: {self.currencies['energy']}/{amount}", context)
            
            # Добавляем сообщение об ошибке как условие
            if self.conditions_processor:
                condition = {
                    "type": "boolean_check",
                    "value": False,
                    "message": message
                }
                
                if not hasattr(context, 'conditions_stack'):
                    context.conditions_stack = []
                
                context.conditions_stack.append({
                    'type': 'if',
                    'condition': condition,
                    'raw': f"require_energy: {amount}",
                    'active': None
                })
            
            return context.current_node, None
        
        # Создаем эффект траты энергии
        effect = {
            "type": "cost",
            "currency": "energy",
            "amount": amount
        }
        
        # Добавляем эффект
        if self.choice_processor and hasattr(self.choice_processor, 'current_choice'):
            if self.choice_processor.current_choice:
                self.choice_processor.add_effect_to_current_choice(effect)
        
        # Тратим энергию
        self._spend_currency('energy', amount, context)
        
        self.log_debug(f"Energy cost: -{amount}", context)
        
        return context.current_node, errors if errors else None
    
    def _check_currency(self, currency: str, amount: int, context: ProcessingContext) -> bool:
        """Проверяет, хватает ли валюты"""
        current = self.currencies.get(currency, 0)
        return current >= amount
    
    def _spend_currency(self, currency: str, amount: int, context: ProcessingContext):
        """Тратит валюту"""
        if currency in self.currencies:
            self.currencies[currency] = max(0, self.currencies[currency] - amount)
            
            # Сохраняем в контексте
            if not hasattr(context, 'currencies'):
                context.currencies = {}
            context.currencies.update(self.currencies)
    
    def add_currency(self, currency: str, amount: int, context: ProcessingContext):
        """Добавляет валюту"""
        if currency in self.currencies:
            self.currencies[currency] += amount
            
            if hasattr(context, 'currencies'):
                context.currencies[currency] = self.currencies[currency]
    
    def get_currency(self, currency: str, context: ProcessingContext) -> int:
        """Возвращает количество валюты"""
        if hasattr(context, 'currencies') and currency in context.currencies:
            return context.currencies[currency]
        return self.currencies.get(currency, 0)
    
    def can_afford(self, costs: List[Dict], context: ProcessingContext) -> Tuple[bool, str]:
        """
        Проверяет, может ли игрок оплатить все costs
        
        Returns:
            Кортеж (может_ли, сообщение_об_ошибке)
        """
        for cost in costs:
            currency = cost.get('currency', 'soft_currency')
            amount = cost.get('amount', 0)
            
            if not self._check_currency(currency, amount, context):
                currency_names = {
                    'soft_currency': 'монет',
                    'hard_currency': 'кристаллов',
                    'energy': 'энергии',
                    'reputation': 'репутации'
                }
                name = currency_names.get(currency, currency)
                return False, f"Недостаточно {name}"
        
        return True, ""


# Экспортируем экземпляр процессора
processor = MonetizationProcessor()