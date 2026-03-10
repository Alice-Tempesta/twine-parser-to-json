"""
Episode metadata parser
Retrieves information about season, episode, titles, etc.
"""

import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..models.episode import EpisodeMetadata
from .tag_parser import TagParser, TagType


class MetadataParser:
    """
    Episode metadata parser
    
    Extracts metadata from the beginning of passages:
    - [SEASON] 1
    - [EPISODE] 1
    - [EPISODE_TITLE] Title
    - etc.
    """
    
    # Metadata can be at the beginning of the file or in a special passage
    METADATA_TAGS = {
        TagType.SEASON: 'season',
        TagType.EPISODE: 'episode',
        TagType.EPISODE_TITLE: 'title',
        TagType.EPISODE_DESC: 'description',
        TagType.EPISODE_COVER: 'cover',
        TagType.EPISODE_ENERGY_COST: 'energy_cost',
        TagType.EPISODE_RELEASE_DATE: 'release_date',
        TagType.EPISODE_REQUIRED: 'required_episode',
    }
    
    @classmethod
    def parse_episode_metadata(cls, text: str) -> Optional[EpisodeMetadata]:
        """
        Parses metadata from passage text
        
        Args:
            text: Passage text
            
        Returns:
            EpisodeMetadata or None if there is no metadata
        """
        lines = text.split('\n')
        metadata_dict = {}
        
        for line in lines[:20]:  # check the first 20 lines
            line = line.strip()
            if not line:
                continue
            
            tag_type, value, params = TagParser.parse_line(line)
            
            if tag_type in cls.METADATA_TAGS:
                field_name = cls.METADATA_TAGS[tag_type]
                
                # Processing the value
                if value is not None:
                    parsed_value = cls._parse_metadata_value(field_name, value)
                    metadata_dict[field_name] = parsed_value
                elif params:
                    # If there are parameters, we take them from there
                    if field_name == 'energy_cost' and 'cost' in params:
                        metadata_dict[field_name] = int(params['cost'])
                    elif field_name == 'required_episode' and 'episode' in params:
                        metadata_dict[field_name] = int(params['episode'])
        
        # Checking that there are required fields
        if 'season' in metadata_dict and 'episode' in metadata_dict:
            # Fill in the default values
            metadata_dict.setdefault('title', f"Эпизод {metadata_dict['episode']}")
            metadata_dict.setdefault('description', "")
            metadata_dict.setdefault('cover', "")
            metadata_dict.setdefault('energy_cost', 1)
            metadata_dict.setdefault('release_date', None)
            metadata_dict.setdefault('required_episode', None)
            
            return EpisodeMetadata(**metadata_dict)
        
        return None
    
    @classmethod
    def _parse_metadata_value(cls, field: str, value: str) -> Any:
        """Parses the metadata value into the correct type"""
        value = value.strip()
        
        if field in ['season', 'episode', 'energy_cost']:
            # Numeric values
            try:
                return int(value)
            except ValueError:
                return 1 if field == 'energy_cost' else 0
        
        elif field == 'required_episode':
            # Special handling 'none'
            if value.lower() == 'none' or not value:
                return None
            try:
                return int(value)
            except ValueError:
                return None
        
        elif field == 'release_date':
            # We parse the date, but leave it as a string if it doesn’t work
            try:
                # Trying different formats
                for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                    try:
                        datetime.strptime(value, fmt)
                        return value
                    except ValueError:
                        continue
            except:
                pass
            return value
        
        else:
            # String values
            return value.strip('"\'')
    
    @classmethod
    def find_episode_passages(cls, passages: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Groups passages by episode based on metadata
        
        Args:
            passages: List of all passages
            
        Returns:
            Dictionary {episode_number: [passage's]}
        """
        episodes = {}
        
        for passage in passages:
            # Trying to find episode metadata
            metadata = cls.parse_episode_metadata(passage['text'])
            
            if metadata:
                # This is a header passage with metadata
                episode_num = metadata.episode
                if episode_num not in episodes:
                    episodes[episode_num] = []
                episodes[episode_num].append(passage)
            else:
                # Regular passage - we determine the episode by context
                # For now we'll just put it in episode 1
                episode_num = 1
                if episode_num not in episodes:
                    episodes[episode_num] = []
                episodes[episode_num].append(passage)
        
        return episodes
    
    @classmethod
    def extract_episode_boundaries(cls, passages: List[Dict]) -> List[Dict[str, Any]]:
        """
        Finds episode boundaries (where a new episode starts)
        
        Returns:
            List of dictionaries with information about the beginning of the episode
        """
        boundaries = []
        current_episode = None
        
        for i, passage in enumerate(passages):
            metadata = cls.parse_episode_metadata(passage['text'])
            
            if metadata:
                if current_episode != metadata.episode:
                    boundaries.append({
                        'index': i,
                        'episode': metadata.episode,
                        'passage': passage['name'],
                        'metadata': metadata
                    })
                    current_episode = metadata.episode
        
        return boundaries
    
    @classmethod
    def get_episode_summary(cls, passages: List[Dict]) -> Dict[int, Dict]:
        """
        Creates a summary of all episodes
        
        Returns:
            Dictionary {episode_number: information}
        """
        summary = {}
        
        for passage in passages:
            metadata = cls.parse_episode_metadata(passage['text'])
            
            if metadata:
                episode_num = metadata.episode
                summary[episode_num] = {
                    'metadata': metadata,
                    'passages': [],
                    'node_count': 0,
                    'start_node': passage['name']
                }
        
        # We count the nodes in each episode
        for passage in passages:
            for episode_num, info in summary.items():
                # Simple heuristic: all passages after metadata before the next metadata
                # (will be improved in episode_builder)
                pass
        
        return summary
    
    @classmethod
    def validate_episode_metadata(cls, metadata: EpisodeMetadata) -> List[str]:
        """Checks the episode metadata for correctness"""
        errors = []
        
        if metadata.season < 1:
            errors.append(f"Invalid season number: {metadata.season}")
        
        if metadata.episode < 1:
            errors.append(f"Invalid episode number: {metadata.episode}")
        
        if metadata.energy_cost < 0:
            errors.append(f"Energy cost cannot be negative: {metadata.energy_cost}")
        
        if metadata.required_episode is not None:
            if metadata.required_episode >= metadata.episode:
                errors.append(
                    f"Required episode {metadata.required_episode} "
                    f"must be before current episode {metadata.episode}"
                )
        
        return errors
    
    @classmethod
    def merge_metadata(cls, metadata_list: List[EpisodeMetadata]) -> Optional[EpisodeMetadata]:
        """
        Combines several metadata (if they are distributed over several passages)
        
        Args:
            metadata_list: List of metadata
            
        Returns:
            Merged metadata
        """
        if not metadata_list:
            return None
        
        if len(metadata_list) == 1:
            return metadata_list[0]
        
        # We take the first one as a basis
        base = metadata_list[0].dict()
        
        # We supplement from the rest
        for metadata in metadata_list[1:]:
            for key, value in metadata.dict().items():
                if value is not None and value != base.get(key):
                    # If the value is different and not empty, use the new one
                    if value not in [None, "", 0, False]:
                        base[key] = value
        
        return EpisodeMetadata(**base)
    
    @classmethod
    def find_start_node(cls, passages: List[Dict], startnode_pid: Optional[str] = None) -> Optional[str]:
        """
        Finds the starting node for the episode
        
        Args:
            passages: List of passages
            startnode_pid: PID of the start node from HTML (optional)
            
        Returns:
            Start node name
        """
        # First we search by PID
        if startnode_pid:
            for passage in passages:
                if passage.get('pid') == startnode_pid:
                    return passage['name']
        
        # We are looking for a passage named init_globals or Start
        for passage in passages:
            name = passage['name'].lower()
            if name in ['init_globals', 'start', 'начало']:
                return passage['name']
        
        # Looking for passage with episode metadata
        for passage in passages:
            metadata = cls.parse_episode_metadata(passage['text'])
            if metadata:
                return passage['name']
        
        # Returning the first passage
        return passages[0]['name'] if passages else None