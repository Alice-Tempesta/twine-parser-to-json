"""
JSON Exporter
Saves history to structured JSON for the game engine.
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from ..models.story import Story
from ..models.episode import Episode
from ..models.node import Node


class JSONExporter:
    """
    JSON exporter

    Features:
    - Beautiful formatting with indents
    - Unicode support
    - Split files by episode
    - Optional minification
    """
    
    def __init__(self, output_dir: str, pretty: bool = True, 
                 split_episodes: bool = True, debug: bool = False):
        """
        Args:
        output_dir: Save directory
        pretty: Pretty formatting
        split_episodes: Split into files by episode
        debug: Debug mode
        """
        self.output_dir = Path(output_dir)
        self.pretty = pretty
        self.split_episodes = split_episodes
        self.debug = debug
        
        # Create a directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export(self, story: Story, filename: str = "story.json") -> List[str]:
        """
        Exports history to JSON.

        Args:
        story: History object
        filename: File name for the full history

        Returns:
        List of created files
        """
        created_files = []
        
        if self.split_episodes:
            # Exporting each episode separately
            episode_files = self._export_episodes(story)
            created_files.extend(episode_files)
            
            # Exporting the index file
            index_file = self._export_index(story, episode_files)
            created_files.append(index_file)
        else:
            # Export everything into one file
            full_file = self._export_full(story, filename)
            created_files.append(full_file)
        
        self._log(f"Exported {len(created_files)} files to {self.output_dir}")
        
        return created_files
    
    def _export_episodes(self, story: Story) -> List[str]:
        """
        Exports each episode to a separate file.

        Returns:
        List of created files.
        """
        created_files = []
        
        for episode_num, episode in story.episodes.items():
            # Forming a file name
            filename = f"episode_{episode_num:02d}.json"
            filepath = self.output_dir / filename
            
            # Convert to dictionary
            episode_dict = self._episode_to_dict(episode, story)
            
            # Save
            self._save_json(episode_dict, filepath)
            created_files.append(str(filepath))
            
            self._log(f"Exported episode {episode_num}: {filename}")
        
        return created_files
    
    def _export_index(self, story: Story, episode_files: List[str]) -> str:
        """
        Exports an index file with links to episodes.

        Returns:
        Path to the created file.
        """
        index = {
            "title": story.metadata.title,
            "author": story.metadata.author,
            "version": story.metadata.version,
            "created": story.metadata.created.isoformat() if story.metadata.created else None,
            "last_modified": story.metadata.last_modified.isoformat() if story.metadata.last_modified else None,
            "ifid": story.metadata.ifid,
            "total_episodes": len(story.episodes),
            "episodes": [],
            "global_variables": {
                name: var.to_dict() 
                for name, var in story.global_variables.items()
            },
            "stats": story.get_stats().dict()
        }
        
        # Adding information about episodes
        for episode_num, episode in story.episodes.items():
            index["episodes"].append({
                "number": episode_num,
                "title": episode.metadata.title,
                "description": episode.metadata.description,
                "cover": episode.metadata.cover,
                "energy_cost": episode.metadata.energy_cost,
                "required_episode": episode.metadata.required_episode,
                "file": f"episode_{episode_num:02d}.json",
                "node_count": len(episode.nodes),
                "start_node": episode.start_node
            })
        
        # Save
        filepath = self.output_dir / "index.json"
        self._save_json(index, filepath)
        
        return str(filepath)
    
    def _export_full(self, story: Story, filename: str) -> str:
        """
        Экспортирует всю историю в один файл
        
        Returns:
            Путь к созданному файлу
        """
        filepath = self.output_dir / filename
        
        # Convert to dictionary
        story_dict = story.to_dict()
        
        # Save
        self._save_json(story_dict, filepath)
        
        return str(filepath)
    
    def _episode_to_dict(self, episode: Episode, story: Story) -> Dict:
        """
        Converts an episode to a dictionary for export.

        Adds global variables and story context.
        """
        episode_dict = episode.to_dict()
        
        # Adding context to the story
        episode_dict["story_context"] = {
            "title": story.metadata.title,
            "ifid": story.metadata.ifid,
            "global_variables": {
                name: var.to_dict() 
                for name, var in story.global_variables.items()
            }
        }
        
        # Adding metadata for the engine
        episode_dict["engine"] = {
            "version": "1.0",
            "type": "visual_novel",
            "features": [
                "choices",
                "inventory",
                "variables",
                "conditions",
                "currency",
                "custom_widgets"
            ]
        }
        
        return episode_dict
    
    def _save_json(self, data: Dict, filepath: Path):
        """Saves data to a JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            if self.pretty:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            else:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'), default=str)
    
    def _log(self, message: str):
        """Logs debug message"""
        if self.debug:
            print(f"[JSONExporter] {message}")

__all__ = ['JSONExporter']