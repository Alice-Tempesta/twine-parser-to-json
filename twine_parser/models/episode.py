"""
Models for game series/episodes
"""

from typing import Dict, List, Optional, Any, ForwardRef
from datetime import datetime
from pydantic import BaseModel, Field

from .flag import GlobalFlag

# For circular references
Node = ForwardRef('Node')


class EpisodeMetadata(BaseModel):
    """Episode metadata"""
    season: int = Field(..., description="Номер сезона")
    episode: int = Field(..., description="Номер эпизода")
    title: str = Field(..., description="Название эпизода")
    description: str = Field(..., description="Описание эпизода")
    cover: str = Field(..., description="Путь к обложке")
    energy_cost: int = Field(1, description="Стоимость энергии для открытия")
    release_date: Optional[str] = Field(None, description="Дата релиза")
    required_episode: Optional[int] = Field(None, description="Какой эпизод нужен для доступа")
    
    class Config:
        validate_assignment = True


class EpisodeState(BaseModel):
    """Initial state of the episode"""
    variables: Dict[str, Any] = Field(default_factory=dict, description="Переменные")
    flags: Dict[str, bool] = Field(default_factory=dict, description="Флаги")
    inventory: List[str] = Field(default_factory=list, description="Инвентарь")
    scene_history: List[str] = Field(default_factory=list, description="История сцен")
    
    class Config:
        validate_assignment = True


class EpisodeSaveData(BaseModel):
    """Data for saving the episode"""
    episode_number: int
    last_node: str
    state: EpisodeState
    saved_at: datetime = Field(default_factory=datetime.now)


class Episode(BaseModel):
    """
    Game series/episode

    Contains all episode data: metadata, initial state,
    all nodes, and a link to the starting node.
    """
    metadata: EpisodeMetadata
    initial_state: EpisodeState
    nodes: Dict[str, Any] = Field(..., description="Словарь нод (id -> Node)")
    start_node: str = Field(..., description="ID стартовой ноды")
    global_functions: Dict[str, Any] = Field(default_factory=dict, description="Глобальные функции")
    
    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
    
    def get_node(self, node_id: str) -> Optional[Any]:
        """Returns a node by ID"""
        return self.nodes.get(node_id)
    
    def validate_links(self) -> List[str]:
        """Checks all links in the episode"""
        errors = []
        for node_id, node in self.nodes.items():
            # Checking next_node_default
            if node.next_node_default and node.next_node_default not in self.nodes:
                errors.append(f"Node '{node_id}': next_node '{node.next_node_default}' not found")
            
            # Checking links in elections
            if hasattr(node, 'choices'):
                for choice in node.choices:
                    if choice.goto and choice.goto not in self.nodes:
                        errors.append(f"Node '{node_id}', choice '{choice.id}': goto '{choice.goto}' not found")
            
            # Checking conditional jumps
            if hasattr(node, 'condition') and node.condition:
                if 'then' in node.condition and node.condition['then'] not in self.nodes:
                    errors.append(f"Node '{node_id}': condition.then '{node.condition['then']}' not found")
                if 'else' in node.condition and node.condition['else'] not in self.nodes:
                    if isinstance(node.condition['else'], str):
                        errors.append(f"Node '{node_id}': condition.else '{node.condition['else']}' not found")
        
        return errors
    
    def to_dict(self) -> dict:
        """Converts to a dictionary for serialization"""
        return {
            "metadata": self.metadata.dict(),
            "initial_state": self.initial_state.dict(),
            "nodes": {k: v.dict() for k, v in self.nodes.items()},
            "start_node": self.start_node,
            "global_functions": self.global_functions
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Episode':
        """Creates from the dictionary"""
        from .node import Node  # Импортируем здесь чтобы избежать циклических импортов
        
        # Converting nodes back to Node objects
        nodes = {}
        for node_id, node_data in data.get('nodes', {}).items():
            nodes[node_id] = Node.from_dict(node_data)
        
        return cls(
            metadata=EpisodeMetadata(**data['metadata']),
            initial_state=EpisodeState(**data.get('initial_state', {})),
            nodes=nodes,
            start_node=data['start_node'],
            global_functions=data.get('global_functions', {})
        )


# Importing Node to resolve circular reference
from .node import Node
Episode.update_forward_refs()