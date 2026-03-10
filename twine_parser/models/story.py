"""
Model for the whole story (collection of all episodes)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from .episode import Episode
from .flag import GlobalFlag


class StoryMetadata(BaseModel):
    """Metadata of the entire history"""
    title: str = Field("Untitled Story", description="Title of the story")
    author: str = Field("Unknown", description="Author")
    version: str = Field("1.0", description="Version")
    created: datetime = Field(default_factory=datetime.now, description="Creation date")
    last_modified: datetime = Field(default_factory=datetime.now, description="Date changes")
    ifid: Optional[str] = Field(None, description="IFID (Interactive Fiction ID)")
    description: Optional[str] = Field(None, description="Description")


class StoryStats(BaseModel):
    """History statistics"""
    total_episodes: int = 0
    total_nodes: int = 0
    total_choices: int = 0
    total_investigation_points: int = 0
    total_characters: int = 0


class Story(BaseModel):
    """
    The whole story (collection of all episodes)
    
    Contains all episodes, global variables and metadata.
    Is the root object during export.
    """
    metadata: StoryMetadata = Field(default_factory=StoryMetadata)
    episodes: Dict[int, Episode] = Field(default_factory=dict, description="Episodes (number -> Episode)")
    global_variables: Dict[str, GlobalFlag] = Field(default_factory=dict, description="Global Variables")
    
    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
    
    def add_episode(self, episode: Episode) -> 'Story':
        """Adds an episode to the story"""
        self.episodes[episode.metadata.episode] = episode
        self.metadata.last_modified = datetime.now()
        return self
    
    def get_episode(self, number: int) -> Optional[Episode]:
        """Returns the episode by number """
        return self.episodes.get(number)
    
    def get_all_episodes(self) -> List[Episode]:
        """Returns all episodes sorted by """
        return [self.episodes[i] for i in sorted(self.episodes.keys())]
    
    def add_global_variable(self, variable: GlobalFlag) -> 'Story':
        """Adds a global variable """
        self.global_variables[variable.name] = variable
        return self
    
    def get_global_variable(self, name: str) -> Optional[GlobalFlag]:
        """Returns a global variable named """
        return self.global_variables.get(name)
    
    def validate_all(self) -> Dict[str, List[str]]:
        """
        Validates the entire history
        Returns a dictionary with errors by episode
        """
        errors = {}
        
        for episode_num, episode in self.episodes.items():
            episode_errors = episode.validate_links()
            if episode_errors:
                errors[f"Episode {episode_num}"] = episode_errors
        
        return errors
    
    def get_stats(self) -> StoryStats:
        """Returns history statistics"""
        stats = StoryStats()
        stats.total_episodes = len(self.episodes)
        
        for episode in self.episodes.values():
            stats.total_nodes += len(episode.nodes)
            
            for node in episode.nodes.values():
                stats.total_choices += len(node.choices)
                stats.total_investigation_points += len(node.investigation_points)
                
                # Unique characters
                for char in node.characters_on_scene:
                    if isinstance(char, dict):
                        char_id = char.get('id')
                    else:
                        char_id = char.id
                    
                    # An easy way to count unique characters
                    # (can be improved)
        
        return stats
    
    def to_dict(self) -> dict:
        """Converts to a dictionary for serialization"""
        return {
            "metadata": self.metadata.dict(),
            "episodes": {
                str(num): episode.to_dict() 
                for num, episode in self.episodes.items()
            },
            "global_variables": {
                name: var.to_dict() 
                for name, var in self.global_variables.items()
            },
            "stats": self.get_stats().dict()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Story':
        """Creates a story from the dictionary"""
        story = cls(
            metadata=StoryMetadata(**data.get('metadata', {})),
            global_variables={}
        )
        
        # Loading episodes
        for num_str, episode_data in data.get('episodes', {}).items():
            episode = Episode.from_dict(episode_data)
            story.episodes[int(num_str)] = episode
        
        # Loading variables
        for name, var_data in data.get('global_variables', {}).items():
            story.global_variables[name] = GlobalFlag.from_dict(var_data)
        
        return story
    
    def export_summary(self) -> str:
        """Вreturns a text description of the story"""
        stats = self.get_stats()
        
        lines = [
            f"📖 {self.metadata.title}",
            f"Author: {self.metadata.author}",
            f"Statistics:",
            f"  • Episodes: {stats.total_episodes}",
            f"  • Total nodes: {stats.total_nodes}",
            f"  • Choices: {stats.total_choices}",
            f"  • Investigation points: {stats.total_investigation_points}",
            f"Created: {self.metadata.created.strftime('%Y-%m-%d %H:%M')}",
            f"Changed: {self.metadata.last_modified.strftime('%Y-%m-%d %H:%M')}"
        ]
        
        if self.metadata.ifid:
            lines.append(f" IFID: {self.metadata.ifid}")
        
        if self.metadata.description:
            lines.append(f"\n {self.metadata.description}")
        
        return "\n".join(lines)