"""
Episode structure validator
Checks the integrity and correctness of episodes
"""

from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

from ..models.story import Story
from ..models.episode import Episode, EpisodeMetadata


class EpisodeValidator:
    """
    Episode structure validator
    
    Checks:
    - Correctness of episode numbers
    - Sequence required_episode
    - Episode metadata
    - Energy cost
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.errors = []
        self.warnings = []
    
    def validate_story(self, story: Story) -> Tuple[List[str], List[str]]:
        """
        Validates all episodes in history
        
        Returns:
            Tuple (errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        self._log("Validating episodes...")
        
        # Checking the sequence of episodes
        self._check_episode_sequence(story)
        
        # We check every episode
        for episode_num, episode in story.episodes.items():
            self._validate_episode(episode, episode_num, story)
        
        self._log(f"Validation complete: {len(self.errors)} errors, {len(self.warnings)} warnings")
        
        return self.errors, self.warnings
    
    def _check_episode_sequence(self, story: Story):
        """Checks the sequence of episodes"""
        
        episode_numbers = sorted(story.episodes.keys())
        
        if not episode_numbers:
            self.errors.append("No episodes found")
            return
        
        # Checking for gaps in numbering
        expected = list(range(episode_numbers[0], episode_numbers[-1] + 1))
        missing = set(expected) - set(episode_numbers)
        
        if missing:
            self.warnings.append(
                f"Missing episodes: {sorted(missing)}. "
                f"This may be intentional if episodes are split across files."
            )
        
        # Checking dependencies
        for episode_num, episode in story.episodes.items():
            required = episode.metadata.required_episode
            
            if required is not None:
                if required >= episode_num:
                    self.errors.append(
                        f"Episode {episode_num} requires episode {required}, "
                        f"but required episode must be before current episode"
                    )
                
                if required not in story.episodes and required != 0:
                    self.warnings.append(
                        f"Episode {episode_num} requires episode {required}, "
                        f"but it doesn't exist"
                    )
    
    def _validate_episode(self, episode: Episode, episode_num: int, story: Story):
        """Validates one episode"""
        
        # Checking the metadata
        self._validate_metadata(episode.metadata, episode_num)
        
        # Checking the starting node
        if episode.start_node not in episode.nodes:
            self.errors.append(
                f"Episode {episode_num}: Start node '{episode.start_node}' "
                f"does not exist in episode nodes"
            )
        
        # We check that there is at least one node
        if not episode.nodes:
            self.errors.append(f"Episode {episode_num}: No nodes found")
        
        # Checking that all nodes have IDs
        for node_id, node in episode.nodes.items():
            if node_id != node.id:
                self.errors.append(
                    f"Episode {episode_num}: Node ID mismatch: "
                    f"'{node_id}' vs '{node.id}'"
                )
    
    def _validate_metadata(self, metadata: EpisodeMetadata, episode_num: int):
        """Checks episode metadata"""
        
        # Checking the number matches
        if metadata.episode != episode_num:
            self.warnings.append(
                f"Episode {episode_num}: Metadata episode number {metadata.episode} "
                f"does not match actual episode number"
            )
        
        # Checking the season
        if metadata.season < 1:
            self.errors.append(f"Episode {episode_num}: Invalid season number {metadata.season}")
        
        # Checking the cost of energy
        if metadata.energy_cost < 0:
            self.errors.append(
                f"Episode {episode_num}: Energy cost cannot be negative: {metadata.energy_cost}"
            )
        elif metadata.energy_cost > 100:
            self.warnings.append(
                f"Episode {episode_num}: Energy cost is very high: {metadata.energy_cost}"
            )
        
        # Checking the cover
        if not metadata.cover:
            self.warnings.append(f"Episode {episode_num}: No cover image specified")
        elif not metadata.cover.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            self.warnings.append(
                f"Episode {episode_num}: Cover '{metadata.cover}' may not be a valid image"
            )
        
        # Checking the release date
        if metadata.release_date:
            try:
                # Checking the date format
                for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d']:
                    try:
                        datetime.strptime(metadata.release_date, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    self.warnings.append(
                        f"Episode {episode_num}: Release date '{metadata.release_date}' "
                        f"may not be in a standard format"
                    )
            except:
                pass
    
    def find_orphaned_nodes(self, episode: Episode) -> List[str]:
        """
        Finds nodes that do not belong to any episode
        (in fact, all the nodes in the episode belong to him)
        """
        return []
    
    def check_episode_continuity(self, story: Story) -> Dict[int, List[str]]:
        """
        Checks plot continuity between episodes
        
        Returns:
            Dictionary {episode: list of problems}
        """
        continuity_issues = defaultdict(list)
        
        episodes = sorted(story.episodes.items())
        
        for i, (episode_num, episode) in enumerate(episodes[:-1]):
            next_episode_num, next_episode = episodes[i + 1]
            
            # Checking if there is a link to the next one at the end of the episode
            has_link_to_next = False
            
            for node in episode.nodes.values():
                # Checking transitions
                if node.next_node_default:
                    # We can't check if it leads to the next episode
                    pass
                
                # Checking the final nodes
                if node.type.value == 'episode_end':
                    has_link_to_next = True
            
            if not has_link_to_next:
                continuity_issues[episode_num].append(
                    f"No clear link to next episode ({next_episode_num})"
                )
        
        return continuity_issues
    
    def _log(self, message: str):
        """Logs debug message"""
        if self.debug:
            print(f"[EpisodeValidator] {message}")


__all__ = ['EpisodeValidator']