"""
History Collector
Combines episodes into a single structure
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.story import Story, StoryMetadata, StoryStats
from ..models.episode import Episode
from ..models.flag import GlobalFlag, VariableType
from ..parsers.html_parser import HTMLParser
from ..parsers.metadata_parser import MetadataParser
from .episode_builder import EpisodeBuilder


class StoryBuilder:
    """
    Collector of the entire history from episodes

    Assembly process:
    1. Group passages by episodes
    2. Build each episode
    3. Combine into a history
    4. Collect global variables
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.episodes = {}
        self.global_variables = {}
        self.errors = []
        self.warnings = []
    
    def build(self, passages: List[Dict], story_metadata: Optional[Dict] = None) -> Optional[Story]:
        """
        Builds the entire story from a list of passages.

        Args:
        passages: List of all passages
        story_metadata: Story metadata (from HTML)

        Returns:
        Story object or None on error
        """
        self._log("Building story...")
        
        # We group passages by episodes
        episodes_data = self._group_by_episodes(passages)
        
        self._log(f"Found {len(episodes_data)} episodes")
        
        # We build every episode
        episode_builder = EpisodeBuilder(debug=self.debug)
        
        for episode_num, episode_passages in episodes_data.items():
            self._log(f"Building episode {episode_num}...")
            
            episode = episode_builder.build_from_passages(episode_passages, episode_num)
            
            if episode:
                self.episodes[episode_num] = episode
                
                # Collecting errors and warnings
                self.errors.extend(episode_builder.get_errors())
                self.warnings.extend(episode_builder.get_warnings())
                
                # Collecting global variables from an episode
                self._collect_variables(episode)
            else:
                self._error(f"Failed to build episode {episode_num}")
        
        if not self.episodes:
            self._error("No episodes were built")
            return None
        
        # Creating story metadata
        metadata = self._create_story_metadata(story_metadata)
        
        # Making history
        story = Story(
            metadata=metadata,
            episodes=self.episodes,
            global_variables=self.global_variables
        )
        
        # Validating the entire story
        validation_errors = story.validate_all()
        for episode_num, errors in validation_errors.items():
            for error in errors:
                self._error(f"Episode {episode_num}: {error}")
        
        # We display statistics
        stats = story.get_stats()
        self._log(f"Story built: {stats.total_episodes} episodes, {stats.total_nodes} nodes")
        
        return story
    
    def _group_by_episodes(self, passages: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Groups passages by episode based on metadata.

        Returns:
        Dictionary {episode_number: [passages]}
        """
        episodes = defaultdict(list)
        
        # First we look for all passages with episode metadata
        episode_boundaries = MetadataParser.extract_episode_boundaries(passages)
        
        if episode_boundaries:
            # Group by found boundaries
            for i, boundary in enumerate(episode_boundaries):
                start_idx = boundary['index']
                end_idx = (episode_boundaries[i + 1]['index'] 
                          if i + 1 < len(episode_boundaries) 
                          else len(passages))
                
                episode_num = boundary['episode']
                episodes[episode_num] = passages[start_idx:end_idx]
                
                self._log(f"Episode {episode_num}: {len(episodes[episode_num])} passages")
        else:
            # No metadata - all in one episode
            self._warning("No episode boundaries found, putting all in episode 1")
            episodes[1] = passages
        
        return dict(episodes)
    
    def _create_story_metadata(self, html_metadata: Optional[Dict]) -> StoryMetadata:
        """Creates story metadata"""
        
        metadata = StoryMetadata(
            title=html_metadata.get('story_name', 'Untitled Story') if html_metadata else 'Untitled Story',
            author="Unknown",
            version="1.0",
            created=datetime.now(),
            last_modified=datetime.now(),
            ifid=html_metadata.get('ifid') if html_metadata else None,
            description=""
        )
        
        return metadata
    
    def _collect_variables(self, episode: Episode):
        """Collects global variables from the episode"""
        for var_name, var_value in episode.initial_state.variables.items():
            if var_name not in self.global_variables:
                # Determining the variable type
                var_type = self._infer_type(var_value)
                
                self.global_variables[var_name] = GlobalFlag(
                    name=var_name,
                    value=var_value,
                    type=var_type,
                    persistent=True
                )
    
    def _infer_type(self, value: Any) -> VariableType:
        """Determines the type of a variable by value"""
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
            return VariableType.STRING
    
    def get_episode(self, number: int) -> Optional[Episode]:
        """Returns the episode by number """
        return self.episodes.get(number)
    
    def get_all_episodes(self) -> List[Episode]:
        """Returns all episodes in numerical order"""
        return [self.episodes[i] for i in sorted(self.episodes.keys())]
    
    def get_errors(self) -> List[str]:
        """Returns a list of errors"""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """Returns a list of warnings"""
        return self.warnings
    
    def _log(self, message: str):
        """Logs debug message"""
        if self.debug:
            print(f"[StoryBuilder] {message}")
    
    def _error(self, message: str):
        """Logs error """
        self.errors.append(message)
        if self.debug:
            print(f"[ERROR] {message}")
    
    def _warning(self, message: str):
        """Logs warning"""
        self.warnings.append(message)
        if self.debug:
            print(f"[WARNING] {message}")


__all__ = ['StoryBuilder']