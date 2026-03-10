"""
Twine HTML parser
Extracts passages and metadata from an HTML structure
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


class HTMLParser:
    """
    Twine HTML parser
    
    Extracts passages from Twine 2 format (Harlowe)
    Supports standard tw-storydata structure
    """
    
    # Regular expressions for parsing
    PASSAGE_PATTERN = re.compile(
        r'<tw-passagedata[^>]*pid="([^"]*)"[^>]*name="([^"]*)"[^>]*>(.*?)</tw-passagedata>',
        re.DOTALL | re.IGNORECASE
    )
    
    STORYDATA_PATTERN = re.compile(
        r'<tw-storydata[^>]*name="([^"]*)"[^>]*startnode="([^"]*)"[^>]*>',
        re.DOTALL | re.IGNORECASE
    )
    
    STYLE_PATTERN = re.compile(
        r'<style[^>]*>(.*?)</style>',
        re.DOTALL | re.IGNORECASE
    )
    
    SCRIPT_PATTERN = re.compile(
        r'<script[^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE
    )
    
    @classmethod
    def parse_file(cls, filepath: str) -> Dict[str, Any]:
        """
        Parses an HTML file and returns a structure with data
        
        Args:
            filepath: Path to the HTML file
            
        Returns:
            Dictionary with data:
            - passages: list of passages
            - story_name: name of the story
            - startnode: ID of the starting node
            - styles: CSS styles
            - scripts: JavaScript code
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return cls.parse_content(content)
    
    @classmethod
    def parse_content(cls, content: str) -> Dict[str, Any]:
        """
        Parses HTML content and returns a structure with data
        
        Args:
            content: HTML content
            
        Returns:
            Dictionary with data
        """
        result = {
            'passages': [],
            'story_name': None,
            'startnode': None,
            'styles': [],
            'scripts': [],
            'ifid': None,
            'format': None,
            'format_version': None
        }
        
        # Extracting story metadata
        storydata_match = cls.STORYDATA_PATTERN.search(content)
        if storydata_match:
            result['story_name'] = storydata_match.group(1)
            result['startnode'] = storydata_match.group(2)
            
            # Extracting additional attributes
            ifid_match = re.search(r'ifid="([^"]*)"', content)
            if ifid_match:
                result['ifid'] = ifid_match.group(1)
            
            format_match = re.search(r'format="([^"]*)"', content)
            if format_match:
                result['format'] = format_match.group(1)
            
            format_version_match = re.search(r'format-version="([^"]*)"', content)
            if format_version_match:
                result['format_version'] = format_version_match.group(1)
        
        # Extracting passages
        for match in cls.PASSAGE_PATTERN.finditer(content):
            pid, name, text = match.groups()
            result['passages'].append({
                'pid': pid,
                'name': name.strip(),
                'text': cls._clean_text(text)
            })
        
        # Extracting styles
        for match in cls.STYLE_PATTERN.finditer(content):
            result['styles'].append(match.group(1).strip())
        
        # Extracting scripts
        for match in cls.SCRIPT_PATTERN.finditer(content):
            result['scripts'].append(match.group(1).strip())
        
        return result
    
    @classmethod
    def _clean_text(cls, text: str) -> str:
        """Clears text from extra spaces and hyphens"""
        # Replace multiple line breaks with single ones
        text = re.sub(r'\n\s*\n', '\n', text)
        # Remove spaces at the beginning and end
        text = text.strip()
        return text
    
    @classmethod
    def extract_passages(cls, content: str) -> List[Dict[str, str]]:
        """
        Extracts only passages from content
        
        Args:
            content: HTML content
            
        Returns:
            List of passages
        """
        result = cls.parse_content(content)
        return result['passages']
    
    @classmethod
    def get_startnode_name(cls, content: str, passages: List[Dict]) -> Optional[str]:
        """
        Finds the name of the starting node by PID
        
        Args:
            content: HTML content
            passages: list of passages
            
        Returns:
            Start node name or None
        """
        storydata = cls.STORYDATA_PATTERN.search(content)
        if not storydata:
            return None
        
        startnode_pid = storydata.group(2)
        
        for passage in passages:
            if passage['pid'] == startnode_pid:
                return passage['name']
        
        return None
    
    @classmethod
    def get_passage_by_name(cls, passages: List[Dict], name: str) -> Optional[Dict]:
        """Finds a passage named """
        for passage in passages:
            if passage['name'] == name:
                return passage
        return None
    
    @classmethod
    def get_passage_by_pid(cls, passages: List[Dict], pid: str) -> Optional[Dict]:
        """Finds passage by PID"""
        for passage in passages:
            if passage['pid'] == pid:
                return passage
        return None
    
    @classmethod
    def validate_passages(cls, passages: List[Dict]) -> List[str]:
        """
        Checks passages for problems
        
        Returns:
            List of errors (empty list if everything is ok)
        """
        errors = []
        names = set()
        pids = set()
        
        for passage in passages:
            name = passage['name']
            pid = passage['pid']
            
            # Checking for duplicate names
            if name in names:
                errors.append(f"Duplicate passage name: {name}")
            names.add(name)
            
            # Checking for duplicate PIDs
            if pid in pids:
                errors.append(f"Duplicate PID: {pid}")
            pids.add(pid)
            
            # Checking empty names
            if not name:
                errors.append(f"Empty passage name for PID {pid}")
        
        return errors