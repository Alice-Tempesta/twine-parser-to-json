"""
Parser of tags in passage text
Parses all types of tags: [TAG], [TAG] value, [[link]]
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum


class TagType(str, Enum):
    """Types of tags"""
    # Metadata
    NODE = "node"
    TITLE = "title"
    HIDDEN = "hidden"
    
    # Media
    BG = "bg"
    MUSIC = "music"
    SOUND = "sound"
    
    # Characters
    CHAR = "char"
    HIDE_CHAR = "hide_char"
    SPEAKER = "speaker"
    
    # Text
    TEXT = "text"
    
    # Navigation
    GOTO = "goto"
    LINK = "link"  # [[link]]
    
    # Elections
    CHOICE = "choice"
    OPTION = "option"
    
    # Conditions
    IF = "if"
    IF_NOT = "if_not"
    AND = "and"
    OR = "or"
    
    # Variables
    SET_GLOBAL = "set_global"
    ADD_GLOBAL = "add_global"
    SAVE_GLOBAL = "save_global"
    GET_GLOBAL = "get_global"
    
    # Items
    GIVE_ITEM = "give_item"
    REMOVE_ITEM = "remove_item"
    CHECK_ITEM = "check_item"
    
    # Monetization
    COST = "cost"
    REQUIRE_ENERGY = "require_energy"
    
    # Custom widgets
    CUSTOM_WIDGET = "custom_widget"
    PARAMS = "params"
    
    # Debugging
    DEBUG = "debug"
    GET_INVENTORY = "get_inventory"
    
    # Episodes
    SEASON = "season"
    EPISODE = "episode"
    EPISODE_TITLE = "episode_title"
    EPISODE_DESC = "episode_desc"
    EPISODE_COVER = "episode_cover"
    EPISODE_ENERGY_COST = "episode_energy_cost"
    EPISODE_RELEASE_DATE = "episode_release_date"
    EPISODE_REQUIRED = "episode_required"
    EPISODE_END = "episode_end"
    RETURN_TO_MENU = "return_to_menu"
    
    # Unknown tag
    UNKNOWN = "unknown"


class TagParser:
    """
    Парсер тегов в тексте passage
    
    Разбирает строки вида:
    - [TAG]
    - [TAG] value
    - [TAG] key = value
    - [[link]]
    - [TAG] {"json": "data"}
    """
    
    # Basic patterns
    TAG_PATTERN = re.compile(r'^\[([A-Za-z_][A-Za-z0-9_]*)\](?:\s*(.*))?$')
    LINK_PATTERN = re.compile(r'\[\[(.*?)\]\]')
    PARAM_PATTERN = re.compile(r'(\w+)\s*=\s*("[^"]*"|\'[^\']*\'|\d+\.?\d*|true|false|null)')
    
    # Mapping tags to enum
    TAG_MAPPING = {
        # Metadata
        '[NODE]': TagType.NODE,
        '[TITLE]': TagType.TITLE,
        '[HIDDEN]': TagType.HIDDEN,
        
        # Media
        '[BG]': TagType.BG,
        '[MUSIC]': TagType.MUSIC,
        '[SOUND]': TagType.SOUND,
        
        # Characters
        '[CHAR]': TagType.CHAR,
        '[HIDE_CHAR]': TagType.HIDE_CHAR,
        '[SPEAKER]': TagType.SPEAKER,
        
        # Text
        '[TEXT]': TagType.TEXT,
        
        # Navigation
        '[GOTO]': TagType.GOTO,
        
        # Elections
        '[CHOICE]': TagType.CHOICE,
        '[OPTION]': TagType.OPTION,
        
        # Conditions
        '[IF]': TagType.IF,
        '[IF_NOT]': TagType.IF_NOT,
        '[AND]': TagType.AND,
        '[OR]': TagType.OR,
        
        # Variables
        '[SET_GLOBAL]': TagType.SET_GLOBAL,
        '[ADD_GLOBAL]': TagType.ADD_GLOBAL,
        '[SAVE_GLOBAL]': TagType.SAVE_GLOBAL,
        '[GET_GLOBAL]': TagType.GET_GLOBAL,
        
        # Items
        '[GIVE_ITEM]': TagType.GIVE_ITEM,
        '[REMOVE_ITEM]': TagType.REMOVE_ITEM,
        '[CHECK_ITEM]': TagType.CHECK_ITEM,
        
        # Monetization
        '[COST]': TagType.COST,
        '[REQUIRE_ENERGY]': TagType.REQUIRE_ENERGY,
        
        # Custom widgets
        '[CUSTOM_WIDGET]': TagType.CUSTOM_WIDGET,
        '[PARAMS]': TagType.PARAMS,
        
        # Debugging
        '[DEBUG]': TagType.DEBUG,
        '[GET_INVENTORY]': TagType.GET_INVENTORY,
        
        # Episodes
        '[SEASON]': TagType.SEASON,
        '[EPISODE]': TagType.EPISODE,
        '[EPISODE_TITLE]': TagType.EPISODE_TITLE,
        '[EPISODE_DESC]': TagType.EPISODE_DESC,
        '[EPISODE_COVER]': TagType.EPISODE_COVER,
        '[EPISODE_ENERGY_COST]': TagType.EPISODE_ENERGY_COST,
        '[EPISODE_RELEASE_DATE]': TagType.EPISODE_RELEASE_DATE,
        '[EPISODE_REQUIRED]': TagType.EPISODE_REQUIRED,
        '[EPISODE_END]': TagType.EPISODE_END,
        '[RETURN_TO_MENU]': TagType.RETURN_TO_MENU,
    }
    
    @classmethod
    def parse_line(cls, line: str) -> Tuple[Optional[TagType], Optional[str], Optional[Dict]]:
        """
       Parses a string and returns (tag_type, value, parameters)
        
        Args:
            line: Line to parse
            
        Returns:
            Tuple (tag_type, value, parameter dictionary)
            If it is not a tag, returns (None, None, None)
        """
        line = line.strip()
        if not line:
            return None, None, None
        
        # Checking for a tag
        tag_match = cls.TAG_PATTERN.match(line)
        if tag_match:
            tag_name = f"[{tag_match.group(1)}]"
            value = tag_match.group(2) if tag_match.group(2) else ""
            
            tag_type = cls.TAG_MAPPING.get(tag_name.upper(), TagType.UNKNOWN)
            
            # Parse parameters if available
            params = cls._parse_params(value) if value else {}
            
            # If these are not JSON parameters, then value is just a string
            if not params and value:
                return tag_type, value.strip(), None
            
            return tag_type, None, params if params else None
        
        return None, None, None
    
    @classmethod
    def _parse_params(cls, text: str) -> Optional[Dict]:
        """Parse the view parameters key=value"""
        # Trying to parse it as JSON
        if text.strip().startswith('{') and text.strip().endswith('}'):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        
        # Let's try to parse key=value pairs
        params = {}
        for match in cls.PARAM_PATTERN.finditer(text):
            key, value = match.groups()
            params[key] = cls._parse_value(value)
        
        return params if params else None
    
    @classmethod
    def _parse_value(cls, value: str) -> Any:
        """Parses value (number, boolean, string)"""
        value = value.strip()
        
        # Numbers
        if value.isdigit():
            return int(value)
        
        # Floating point numbers
        try:
            if '.' in value:
                return float(value)
        except ValueError:
            pass
        
        # Boolean values
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        if value.lower() == 'null':
            return None
        
        # Quoted strings
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        # Regular lines
        return value
    
    @classmethod
    def extract_links(cls, text: str) -> List[str]:
        """Extracts all links [[title]] from text"""
        return cls.LINK_PATTERN.findall(text)
    
    @classmethod
    def replace_links(cls, text: str, replacement: str = "[LINK]") -> str:
        """Replaces links to placeholder """
        return cls.LINK_PATTERN.sub(replacement, text)
    
    @classmethod
    def is_tag_line(cls, line: str) -> bool:
        """Checks if a string is a tag""" 
        return bool(cls.TAG_PATTERN.match(line.strip()))
    
    @classmethod
    def is_comment(cls, line: str) -> bool:
        """Checks if a string is a comment"""
        return line.strip().startswith('//')
    
    @classmethod
    def parse_effect(cls, tag_type: TagType, value: Optional[str], params: Optional[Dict]) -> Optional[Dict]:
        """
        Parses the effect from the tag
        
        Args:
            tag_type: Tag type
            value: Value (if any)
            params: Parameters (if any)
            
        Returns:
            Dictionary with effect or None
        """
        if tag_type == TagType.SET_GLOBAL:
            if value and '=' in value:
                var_name, var_value = value.split('=', 1)
                return {
                    "type": "modify_variable",
                    "variable": var_name.strip(),
                    "operation": "set",
                    "value": cls._parse_value(var_value.strip())
                }
            elif params:
                return {
                    "type": "modify_variable",
                    "variable": params.get('name'),
                    "operation": "set",
                    "value": params.get('value')
                }
        
        elif tag_type == TagType.ADD_GLOBAL:
            if value and '=' in value:
                var_name, var_value = value.split('=', 1)
                return {
                    "type": "modify_variable",
                    "variable": var_name.strip(),
                    "operation": "add",
                    "value": cls._parse_value(var_value.strip())
                }
            elif params:
                return {
                    "type": "modify_variable",
                    "variable": params.get('name'),
                    "operation": "add",
                    "value": params.get('value', 1)
                }
        
        elif tag_type == TagType.GIVE_ITEM:
            if value:
                return {
                    "type": "add_item",
                    "item": value.strip()
                }
            elif params:
                return {
                    "type": "add_item",
                    "item": params.get('item') or params.get('name')
                }
        
        elif tag_type == TagType.REMOVE_ITEM:
            if value:
                return {
                    "type": "remove_item",
                    "item": value.strip()
                }
            elif params:
                return {
                    "type": "remove_item",
                    "item": params.get('item') or params.get('name')
                }
        
        elif tag_type == TagType.COST:
            if value and '=' in value:
                currency, amount = value.split('=', 1)
                return {
                    "type": "cost",
                    "currency": currency.strip(),
                    "amount": cls._parse_value(amount.strip())
                }
            elif params:
                return {
                    "type": "cost",
                    "currency": params.get('currency', 'soft'),
                    "amount": params.get('amount', 0)
                }
        
        elif tag_type == TagType.SAVE_GLOBAL:
            if value:
                return {
                    "type": "save_variable",
                    "variable": value.strip()
                }
            elif params:
                return {
                    "type": "save_variable",
                    "variable": params.get('name')
                }
        
        return None
    
    @classmethod
    def parse_condition(cls, condition_text: str) -> Dict:
        """
        Parses a condition like [IF] variable == value
        
        Args:
            condition_text: Condition text
            
        Returns:
            Dictionary with condition
        """
        condition_text = condition_text.strip()
        
        # Simple Operators
        operators = [
            ('==', 'eq'), ('!=', 'ne'), 
            ('>=', 'ge'), ('<=', 'le'),
            ('>', 'gt'), ('<', 'lt'),
            (' contains ', 'contains'),
            (' in ', 'in'),
            (' is ', 'is'),
            (' is not ', 'is_not')
        ]
        
        for op_str, op_name in operators:
            if op_str in condition_text:
                parts = condition_text.split(op_str, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = cls._parse_value(parts[1].strip())
                    
                    # Checking whether it is a variable or a value
                    if left.startswith('$') or left.startswith('_'):
                        var_name = left[1:] if left.startswith('$') else left
                        return {
                            "type": "variable_check",
                            "variable": var_name,
                            "operator": op_name,
                            "value": right
                        }
                    else:
                        return {
                            "type": "direct_check",
                            "left": cls._parse_value(left),
                            "operator": op_name,
                            "right": right
                        }
        
        # If there is no operator, just a boolean value
        return {
            "type": "boolean_check",
            "value": cls._parse_value(condition_text)
        }