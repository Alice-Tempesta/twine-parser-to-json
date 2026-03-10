"""
Models for game nodes/scenes
"""

from typing import List, Dict, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Node types"""
    CUTSCENE = "cutscene"              # cutscene without interactions
    DIALOGUE = "dialogue"               # simple dialogue
    DIALOGUE_WITH_CHOICES = "dialogue_with_choices"  # dialog with choice
    INVESTIGATION = "investigation"     #point of investigation
    CHARACTER_CREATOR = "character_creator"  # character creation
    QUICKTIME = "quicktime"              # QTE event
    MINIGAME = "minigame"                 # mini-game
    EPISODE_END = "episode_end"           # end of episode
    HIDDEN = "hidden"                      # hidden node (for variables)


class MediaAsset(BaseModel):
    """media resource"""
    file: str = Field(..., description="Путь к файлу")
    loop: bool = Field(False, description="Зациклить?")
    volume: float = Field(1.0, description="Громкость (0-1)")
    
    class Config:
        validate_assignment = True


class CharacterPosition(str, Enum):
    """Character's position on stage"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    LEFT_CENTER = "left_center"
    RIGHT_CENTER = "right_center"
    OFF_SCREEN = "off_screen"


class CharacterEmotion(str, Enum):
    """Character's emotions"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    SCARED = "scared"
    THINKING = "thinking"
    SARCASTIC = "sarcastic"
    SERIOUS = "serious"
    ANNOYED = "annoyed"
    AMUSED = "amused"
    CURIOUS = "curious"
    DESPERATE = "desperate"
    DEFENSIVE = "defensive"
    POLITE = "polite"


class CharacterOnScene(BaseModel):
    """Character on stage"""
    id: str = Field(..., description="ID персонажа")
    sprite: str = Field(..., description="Имя спрайта")
    position: CharacterPosition = Field(CharacterPosition.CENTER, description="Позиция")
    emotion: CharacterEmotion = Field(CharacterEmotion.NEUTRAL, description="Эмоция")
    animation: str = Field("idle", description="Анимация")
    flip: bool = Field(False, description="Отразить по горизонтали?")
    visible: bool = Field(True, description="Видим?")


class ContentType(str, Enum):
    """Content types"""
    NARRATION = "narration"          #narrative
    DIALOGUE = "dialogue"             # dialogue
    ACTION = "action"                 # action/description
    STAGE_DIRECTION = "stage_direction"  # trailer
    SOUND = "sound"                   # sound
    MUSIC = "music"                    # music
    WAIT = "wait"                      # pause
    CUSTOM = "custom"  # custom widget
    DEBUG = "debug"    # debugging information


class ContentItem(BaseModel):
    """Content element"""
    type: ContentType = Field(..., description="Content type")
    speaker: Optional[str] = Field(None, description="Speaker (for dialogue)")
    text: Optional[str] = Field(None, description="Text")
    description: Optional[str] = Field(None, description="Description of action")
    file: Optional[str] = Field(None, description="File (for sound/music)")
    emotion: CharacterEmotion = Field(CharacterEmotion.NEUTRAL, description="Emotion")
    duration: Optional[float] = Field(None, description="Duration (for pause)")
    
    class Config:
        use_enum_values = True


class EffectType(str, Enum):
    """Effect types"""
    MODIFY_VARIABLE = "modify_variable"
    SET_FLAG = "set_flag"
    ADD_ITEM = "add_item"
    REMOVE_ITEM = "remove_item"
    ADD_CLUE = "add_clue"
    PLAY_SOUND = "play_sound"
    PLAY_MUSIC = "play_music"
    STOP_MUSIC = "stop_music"
    COST = "cost"
    CUSTOM = "custom"


class Effect(BaseModel):
    """Action effect"""
    type: EffectType = Field(..., description="Effect type")
    
    # For variables
    variable: Optional[str] = Field(None, description="Variable name")
    operation: Optional[str] = Field(None, description="Operation (add/set/multiply/etc)")
    value: Optional[Any] = Field(None, description="Meaning")
    
    # For flags
    flag: Optional[str] = Field(None, description="Flag name")
    
    # For items
    item: Optional[str] = Field(None, description="Item")
    
    # For currency
    currency: Optional[str] = Field(None, description="Currency type")
    amount: Optional[int] = Field(None, description="Quantity")
    
    # For media
    sound: Optional[str] = Field(None, description="Sound")
    music: Optional[str] = Field(None, description="Music")
    
    # For custom effects
    custom_data: Optional[Dict] = Field(None, description="Custom data")


class Choice(BaseModel):
    """Selection option"""
    id: str = Field(..., description="Selection ID")
    text: str = Field(..., description="Selection text")
    enabled: bool = Field(True, description="Available?")
    visible: bool = Field(True, description="We see?")
    effects: List[Effect] = Field(default_factory=list, description="Selection effects")
    goto: Optional[str] = Field(None, description="Next node ID")
    condition: Optional[Dict] = Field(None, description="Condition for display")


class InvestigationPointType(str, Enum):
    """Types of investigation points"""
    EXAMINE = "examine"    # inspect
    SEARCH = "search"      # search
    TALK = "talk"          # talk
    USE = "use"            # use item


class InvestigationPoint(BaseModel):
    """Investigation point"""
    id: str = Field(..., description="Point ID")
    type: InvestigationPointType = Field(..., description="Type")
    name: str = Field(..., description="Name")
    description: str = Field(..., description="Description")
    
    # Requirements
    required_skill: Optional[str] = Field(None, description="Required Skill")
    required_skill_value: Optional[int] = Field(None, description="Skill value")
    required_item: Optional[str] = Field(None, description="Required item")
    
    # Lyrics
    success_text: Optional[str] = Field(None, description="Text on success")
    failure_text: Optional[str] = Field(None, description="Text on failure")
    
    # Effects
    success_effects: List[Effect] = Field(default_factory=list, description="Effects on Success")
    
    # Clues
    clues: List[Dict] = Field(default_factory=list, description="Evidence found")


class Transition(BaseModel):
    """Transitions when entering/exiting a node"""
    on_enter: List[Effect] = Field(default_factory=list, description="Entry Effects")
    on_exit: List[Effect] = Field(default_factory=list, description="Exit effects")


class Condition(BaseModel):
    """Conditional jump"""
    type: str = Field(..., description="Condition type (if/if_not)")
    condition: str = Field(..., description="Condition")
    then: Union[str, Dict] = Field(..., description="What to do if true")
    else_: Optional[Union[str, Dict]] = Field(None, description="What to do if false", alias="else")


class Node(BaseModel):
    """Node/scene"""
    id: str = Field(..., description="Node ID")
    type: NodeType = Field(NodeType.DIALOGUE, description="Node type")
    title: str = Field("", description="Heading")
    hidden: bool = Field(False, description="Hidden node?")
    
    # Media
    media: Dict[str, Any] = Field(
        default_factory=lambda: {
            "background": "",
            "music": "",
            "sounds": []
        },
        description="Media resource"
    )
    
    # Characters
    characters_on_scene: List[CharacterOnScene] = Field(
        default_factory=list,
        description="Characters on stage"
    )
    
    # Content
    content: List[ContentItem] = Field(
        default_factory=list,
        description="Node content"
    )
    
    # Elections
    choices: List[Choice] = Field(
        default_factory=list,
        description="Choices"
    )
    
    # Investigation
    investigation_points: List[InvestigationPoint] = Field(
        default_factory=list,
        description="Investigation points"
    )
    
    # Transitions
    transitions: Transition = Field(
        default_factory=Transition,
        description="Transitions"
    )
    
    # Next node by default
    next_node_default: Optional[str] = Field(
        None,
        description="Next node by default"
    )
    
    # Conditional jump
    condition: Optional[Condition] = Field(
        None,
        description="Conditional jump"
    )
    
    # Character customization
    character_customization: Optional[Dict] = Field(
        None,
        description="Data for customization"
    )

    # Custom widgets
    widgets: List[str] = Field(
        default_factory=list,
        description="IDs of widgets used in the node"
    )
    
    widget_instances: Dict[str, Any] = Field(
        default_factory=dict,
        description="Widget instances in this node"
    )
    
    class Config:
        use_enum_values = True
        validate_assignment = True
        allow_population_by_field_name = True
    
    def add_content(self, item: ContentItem) -> 'Node':
        """Adds a content element"""
        self.content.append(item)
        return self
    
    def add_choice(self, choice: Choice) -> 'Node':
        """Adds a selection option"""
        self.choices.append(choice)
        return self
    
    def add_character(self, character: CharacterOnScene) -> 'Node':
        """Adds a character to the scene"""
        # Checking to see if there is already such a character
        for i, c in enumerate(self.characters_on_scene):
            if c.id == character.id:
                self.characters_on_scene[i] = character
                return self
        
        self.characters_on_scene.append(character)
        return self
    
    def remove_character(self, character_id: str) -> 'Node':
        """Removes a character from the stage"""
        self.characters_on_scene = [
            c for c in self.characters_on_scene if c.id != character_id
        ]
        return self
    
    def set_background(self, background: str) -> 'Node':
        """Sets the background"""
        self.media["background"] = background
        return self
    
    def set_music(self, music: str) -> 'Node':
        """Sets the music"""
        self.media["music"] = music
        return self
    
    def add_sound(self, sound: Union[str, MediaAsset]) -> 'Node':
        """Adds sound"""
        if isinstance(sound, str):
            sound = MediaAsset(file=sound)
        
        if not isinstance(self.media["sounds"], list):
            self.media["sounds"] = []
        
        self.media["sounds"].append(sound.dict() if isinstance(sound, MediaAsset) else sound)
        return self
    
    def to_dict(self) -> dict:
        """Converts to a dictionary for serialization"""
        result = {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, NodeType) else self.type,
            "title": self.title,
            "hidden": self.hidden,
            "media": self.media,
            "characters_on_scene": [
                c.dict() if isinstance(c, CharacterOnScene) else c
                for c in self.characters_on_scene
            ],
            "content": [
                c.dict() if isinstance(c, ContentItem) else c
                for c in self.content
            ],
            "choices": [
                c.dict() if isinstance(c, Choice) else c
                for c in self.choices
            ],
            "investigation_points": [
                i.dict() if isinstance(i, InvestigationPoint) else i
                for i in self.investigation_points
            ],
            "transitions": self.transitions.dict() if isinstance(self.transitions, Transition) else self.transitions,
            "next_node_default": self.next_node_default
        }
        
        if self.condition:
            result["condition"] = self.condition.dict() if isinstance(self.condition, Condition) else self.condition
        
        if self.character_customization:
            result["character_customization"] = self.character_customization
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Node':
        """Creates from the dictionary"""
        # Converting nested objects
        if 'characters_on_scene' in data:
            data['characters_on_scene'] = [
                CharacterOnScene(**c) if isinstance(c, dict) else c
                for c in data['characters_on_scene']
            ]
        
        if 'content' in data:
            data['content'] = [
                ContentItem(**c) if isinstance(c, dict) else c
                for c in data['content']
            ]
        
        if 'choices' in data:
            data['choices'] = [
                Choice(**c) if isinstance(c, dict) else c
                for c in data['choices']
            ]
        
        if 'investigation_points' in data:
            data['investigation_points'] = [
                InvestigationPoint(**i) if isinstance(i, dict) else i
                for i in data['investigation_points']
            ]
        
        if 'transitions' in data and isinstance(data['transitions'], dict):
            data['transitions'] = Transition(**data['transitions'])
        
        if 'condition' in data and isinstance(data['condition'], dict):
            data['condition'] = Condition(**data['condition'])
        
        # Convert type to NodeType if it is a string
        if 'type' in data and isinstance(data['type'], str):
            try:
                data['type'] = NodeType(data['type'])
            except ValueError:
                pass  # оставляем как есть
        
        return cls(**data)