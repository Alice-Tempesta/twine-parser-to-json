"""
Episode Collector
"""

from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from ..models.episode import Episode, EpisodeMetadata, EpisodeState
from ..models.node import Node, NodeType, ContentItem, ContentType
from ..parsers.html_parser import HTMLParser
from ..parsers.tag_parser import TagParser, TagType
from ..parsers.metadata_parser import MetadataParser
from ..processors.tag_processor import ProcessingContext
from ..processors.processors import ALL_PROCESSORS, PROCESSOR_MAP


class EpisodeBuilder:
    """
    Episode Assembler

    Assembly process:
    1. Find episode metadata
    2. Create all nodes, processing tags with processors
    3. Link nodes together
    4. Validate structure
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.current_episode_num = None
        self.current_node = None
        self.all_nodes = {}
        self.variables = {}
        self.inventory = {}
        self.currencies = {
            'soft_currency': 100,
            'hard_currency': 0,
            'energy': 10,
            'reputation': 0
        }
        self.errors = []
        self.warnings = []
    
    def build_from_passages(
        self, 
        passages: List[Dict], 
        episode_num: Optional[int] = None
    ) -> Optional[Episode]:
        """
        Builds an episode from a list

        Args:
        passages: List of passages
        episode_num: Episode number (if known)
                    
        Returns:
            Episode объект или None при ошибке
        """
        self._log(f"Building episode {episode_num if episode_num else 'unknown'}")
        
        # Sort passages by PID to maintain order
        passages = sorted(passages, key=lambda p: int(p.get('pid', 0)))
        
        # Finding the episode metadata
        metadata = self._find_episode_metadata(passages)
        if not metadata and episode_num:
            # Creating basic metadata
            metadata = EpisodeMetadata(
                season=1,
                episode=episode_num,
                title=f"Episode {episode_num}",
                description="",
                cover="",
                energy_cost=1
            )
        
        if not metadata:
            self._error("Could not find episode metadata")
            return None
        
        self.current_episode_num = metadata.episode
        
        # Resetting the state
        self.all_nodes = {}
        self.current_node = None
        
        # We process every passage
        for passage in passages:
            self._process_passage(passage)
        
        # Finding the starting node
        start_node = self._find_start_node(passages)
        
        if not start_node and self.all_nodes:
            # Take the first node
            start_node = next(iter(self.all_nodes.values())).id
        
        if not start_node:
            self._error("No start node found")
            return None
        
        # Create the initial state
        initial_state = EpisodeState(
            variables={k: v.value if hasattr(v, 'value') else v 
                      for k, v in self.variables.items()},
            flags={},
            inventory=list(self.inventory.keys()),
            scene_history=[]
        )
        
        # Creating an episode
        episode = Episode(
            metadata=metadata,
            initial_state=initial_state,
            nodes=self.all_nodes,
            start_node=start_node,
            global_functions=self._get_global_functions()
        )
        
        # Validable
        validation_errors = episode.validate_links()
        if validation_errors:
            for error in validation_errors:
                self._error(error)
        
        self._log(f"Episode built: {len(self.all_nodes)} nodes, start: {start_node}")
        
        return episode
    
    def _process_passage(self, passage: Dict):
        """Processes one passage"""
        passage_name = passage['name']
        passage_text = passage['text']
        lines = passage_text.split('\n')
        
        self._log(f"Processing passage: {passage_name}")
        
        # Context for processors
        context = ProcessingContext(
            current_node=self.current_node,
            current_episode_num=self.current_episode_num,
            all_nodes=self.all_nodes,
            variables=self.variables,
            debug=self.debug
        )
        
        # Adding additional attributes
        context.inventory = self.inventory
        context.currencies = self.currencies
        
        line_number = 0
        in_choice_block = False
        
        for line in lines:
            line_number += 1
            line = line.strip()
            
            if not line or line.startswith('//'):
                # Skip empty lines and comments
                continue
            
            # Parsim teg
            tag_type, value, params = TagParser.parse_line(line)
            
            if tag_type:
                # Found a tag
                self._log(f"  Line {line_number}: {tag_type.value} = {value or params}")
                
                # Getting processors for this tag
                processors = PROCESSOR_MAP.get(tag_type, [])
                
                if not processors:
                    self._warning(f"No processor for tag: {tag_type.value}")
                    continue
                
                # We process the tag with each processor
                for processor in processors:
                    try:
                        updated_node, errors = processor.process(
                            tag_type, value, params, context, line_number
                        )
                        
                        if errors:
                            for error in errors:
                                self._error(f"Line {line_number}: {error}")
                        
                        if updated_node:
                            self.current_node = updated_node
                            self.all_nodes[updated_node.id] = updated_node
                            context.current_node = updated_node
                    
                    except Exception as e:
                        self._error(f"Line {line_number}: Processor error - {str(e)}")
                
                # Special processing for selection blocks
                if tag_type == TagType.CHOICE:
                    in_choice_block = True
                elif tag_type == TagType.OPTION:
                    pass  # already processed
                
            elif TagParser.extract_links(line):
                # The line contains links, processed as content
                self._process_content_line(line, context, line_number)
            
            elif not in_choice_block:
                # Plain text outside the select box
                self._process_content_line(line, context, line_number)
        
        # We complete the selection block if there was one
        if in_choice_block:
            from ..processors.processors.choice import processor as choice_processor
            choice_processor.end_choice_block(context)
        
        # Clearing the conditions after processing the node
        if hasattr(context, 'conditions_stack'):
            delattr(context, 'conditions_stack')
    
    def _process_content_line(self, line: str, context: ProcessingContext, line_number: int):
        """Treats a string as content"""
        if not self.current_node:
            # Create a temporary node if there is no current one
            from ..models.node import Node
            self.current_node = Node(id=f"temp_node_{line_number}")
            self.all_nodes[self.current_node.id] = self.current_node
            context.current_node = self.current_node
        
        # Using ContentProcessor
        from ..processors.processors.content import processor as content_processor
        
        try:
            updated_node, errors = content_processor.process(
                TagType.UNKNOWN, line, None, context, line_number
            )
            
            if errors:
                for error in errors:
                    self._error(f"Line {line_number}: {error}")
            
            if updated_node:
                self.current_node = updated_node
                self.all_nodes[updated_node.id] = updated_node
                context.current_node = updated_node
        
        except Exception as e:
            self._error(f"Line {line_number}: Content error - {str(e)}")
    
    def _find_episode_metadata(self, passages: List[Dict]) -> Optional[EpisodeMetadata]:
        """Looks up episode metadata in passages"""
        for passage in passages:
            metadata = MetadataParser.parse_episode_metadata(passage['text'])
            if metadata:
                return metadata
        return None
    
    def _find_start_node(self, passages: List[Dict]) -> Optional[str]:
        """Finds the start node of the episode """
        # We are looking for a node named init_globals or Start
        for node_id, node in self.all_nodes.items():
            if node_id.lower() in ['init_globals', 'start']:
                return node_id
        
        # We are looking for a node with metadata
        for passage in passages:
            metadata = MetadataParser.parse_episode_metadata(passage['text'])
            if metadata and passage['name'] in self.all_nodes:
                return passage['name']
        
        # Returning the first node
        if self.all_nodes:
            return next(iter(self.all_nodes.keys()))
        
        return None
    
    def _get_global_functions(self) -> Dict:
        """Returns a dictionary of global functions for the engine"""
        return {
            "check_condition": {
                "always": {"type": "constant", "value": True},
                "has_item": {"type": "inventory_check"},
                "variable_check": {"type": "variable_comparison"},
                "flag_check": {"type": "flag_check"},
                "energy_check": {"type": "energy_check"},
                "currency_check": {"type": "currency_check"}
            },
            "effect_types": {
                "modify_variable": {"requires": ["variable", "operation", "value"]},
                "set_flag": {"requires": ["flag", "value"]},
                "add_item": {"requires": ["item", "item_data"]},
                "remove_item": {"requires": ["item", "quantity"]},
                "add_clue": {"requires": ["clue"]},
                "play_sound": {"requires": ["sound"]},
                "play_music": {"requires": ["music"]},
                "stop_music": {},
                "cost": {"requires": ["currency", "amount"]},
                "custom_widget": {"requires": ["widget_id", "params"]}
            }
        }
    
    def _log(self, message: str):
        """Logs debug message"""
        if self.debug:
            print(f"[EpisodeBuilder] {message}")
    
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
    
    def get_errors(self) -> List[str]:
        """Returns a list of errors"""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """Returns a list of warnings"""
        return self.warnings


# We export
__all__ = ['EpisodeBuilder']