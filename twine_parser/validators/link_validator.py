"""
Validator of links between nodes
Checks that all transitions lead to existing nodes
"""

from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from ..models.story import Story
from ..models.episode import Episode
from ..models.node import Node


class LinkValidator:
    """
    Validator of links between nodes
    
    Checks:
    - Do all transitions (goto) lead to existing nodes?
    - Are there any cyclic dependencies?
    - Are all nodes reachable from the starting node?
    - Are there any “dead” nodes (to which no one refers)
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.errors = []
        self.warnings = []
    
    def validate_story(self, story: Story) -> Tuple[List[str], List[str]]:
        """
        Validates all links in the entire history
        
        Returns:
            Tuple (errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        self._log("Validating story links...")
        
        all_nodes = set()
        node_to_episode = {}
        
        # Collecting all nodes from all episodes
        for episode_num, episode in story.episodes.items():
            for node_id in episode.nodes.keys():
                all_nodes.add(node_id)
                node_to_episode[node_id] = episode_num
        
        # We check every episode
        for episode_num, episode in story.episodes.items():
            self._validate_episode(episode, episode_num, all_nodes, node_to_episode)
        
        # We check reachability in each episode
        for episode_num, episode in story.episodes.items():
            self._check_reachability(episode, episode_num)
        
        self._log(f"Validation complete: {len(self.errors)} errors, {len(self.warnings)} warnings")
        
        return self.errors, self.warnings
    
    def _validate_episode(
        self, 
        episode: Episode, 
        episode_num: int,
        all_nodes: Set[str],
        node_to_episode: Dict[str, int]
    ):
        """Validates links in one episode"""
        
        for node_id, node in episode.nodes.items():
            # Checking next_node_default
            if node.next_node_default:
                self._check_link(
                    node.next_node_default,
                    node_id,
                    "next_node_default",
                    episode_num,
                    all_nodes,
                    node_to_episode
                )
            
            # Checking links in elections
            for choice in node.choices:
                if isinstance(choice, dict):
                    goto = choice.get('goto')
                    if goto:
                        self._check_link(
                            goto,
                            node_id,
                            f"choice '{choice.get('text', '')[:30]}...'",
                            episode_num,
                            all_nodes,
                            node_to_episode
                        )
                elif hasattr(choice, 'goto') and choice.goto:
                    self._check_link(
                        choice.goto,
                        node_id,
                        f"choice '{choice.text[:30]}...'",
                        episode_num,
                        all_nodes,
                        node_to_episode
                    )
            
            # Checking conditional jumps
            if node.condition:
                if hasattr(node.condition, 'then') and node.condition.then:
                    if isinstance(node.condition.then, str):
                        self._check_link(
                            node.condition.then,
                            node_id,
                            "condition.then",
                            episode_num,
                            all_nodes,
                            node_to_episode
                        )
                
                if hasattr(node.condition, 'else_') and node.condition.else_:
                    if isinstance(node.condition.else_, str):
                        self._check_link(
                            node.condition.else_,
                            node_id,
                            "condition.else",
                            episode_num,
                            all_nodes,
                            node_to_episode
                        )
    
    def _check_link(
        self,
        target: str,
        source_node: str,
        link_type: str,
        episode_num: int,
        all_nodes: Set[str],
        node_to_episode: Dict[str, int]
    ):
        """Checks one link"""
        
        if target not in all_nodes:
            self.errors.append(
                f"Episode {episode_num}: {link_type} in node '{source_node}' "
                f"targets '{target}' which does not exist"
            )
        elif node_to_episode.get(target) != episode_num:
            # Link to another episode - warning
            target_episode = node_to_episode.get(target)
            self.warnings.append(
                f"Episode {episode_num}: {link_type} in node '{source_node}' "
                f"targets '{target}' in episode {target_episode} "
                f"(cross-episode links are allowed but need careful handling)"
            )
    
    def _check_reachability(self, episode: Episode, episode_num: int):
        """
        Checks whether all nodes in the episode are reachable from the start node
        
        Uses depth-first search to build a reachability graph
        """
        if not episode.start_node:
            self.errors.append(f"Episode {episode_num}: No start node defined")
            return
        
        if episode.start_node not in episode.nodes:
            self.errors.append(
                f"Episode {episode_num}: Start node '{episode.start_node}' "
                f"does not exist"
            )
            return
        
        # Building a reachability graph
        visited = set()
        stack = [episode.start_node]
        
        while stack:
            current_id = stack.pop()
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            if current_id not in episode.nodes:
                continue
            
            current = episode.nodes[current_id]
            
            # Add next_node_default
            if current.next_node_default:
                stack.append(current.next_node_default)
            
            # Adding elections
            for choice in current.choices:
                if isinstance(choice, dict):
                    goto = choice.get('goto')
                    if goto:
                        stack.append(goto)
                elif hasattr(choice, 'goto') and choice.goto:
                    stack.append(choice.goto)
            
            # Adding conditional jumps
            if current.condition:
                if hasattr(current.condition, 'then') and current.condition.then:
                    if isinstance(current.condition.then, str):
                        stack.append(current.condition.then)
                if hasattr(current.condition, 'else_') and current.condition.else_:
                    if isinstance(current.condition.else_, str):
                        stack.append(current.condition.else_)
        
        # Finding unreachable nodes
        all_nodes = set(episode.nodes.keys())
        unreachable = all_nodes - visited
        
        if unreachable:
            # Sort for beautiful output
            unreachable_list = sorted(unreachable)
            if len(unreachable_list) > 10:
                self.warnings.append(
                    f"Episode {episode_num}: {len(unreachable_list)} nodes are unreachable "
                    f"from start node '{episode.start_node}'"
                )
            else:
                self.warnings.append(
                    f"Episode {episode_num}: Unreachable nodes: {', '.join(unreachable_list)}"
                )
    
    def find_dead_nodes(self, episode: Episode) -> List[str]:
        """
       Finds "dead" nodes - those that no one links to
        
        Returns:
            List of node IDs that have no links
        """
        referenced = set()
        
        # Collecting all links
        for node_id, node in episode.nodes.items():
            if node.next_node_default:
                referenced.add(node.next_node_default)
            
            for choice in node.choices:
                if isinstance(choice, dict):
                    goto = choice.get('goto')
                    if goto:
                        referenced.add(goto)
                elif hasattr(choice, 'goto') and choice.goto:
                    referenced.add(choice.goto)
            
            if node.condition:
                if hasattr(node.condition, 'then') and node.condition.then:
                    if isinstance(node.condition.then, str):
                        referenced.add(node.condition.then)
                if hasattr(node.condition, 'else_') and node.condition.else_:
                    if isinstance(node.condition.else_, str):
                        referenced.add(node.condition.else_)
        
        # The starting node is considered referenced
        if episode.start_node:
            referenced.add(episode.start_node)
        
        # Finding nodes that have no links
        all_nodes = set(episode.nodes.keys())
        dead_nodes = all_nodes - referenced
        
        return sorted(dead_nodes)
    
    def find_cycles(self, episode: Episode) -> List[List[str]]:
        """
        Finds cyclic dependencies in the node graph
        
        Returns:
            List of cycles (each cycle is a list of node IDs)
        """
        cycles = []
        visited = set()
        path = []
        
        def dfs(node_id: str, path_set: Set[str]):
            if node_id in path_set:
                # Found a cycle
                cycle_start = path.index(node_id) if node_id in path else 0
                cycle = path[cycle_start:] + [node_id]
                if cycle not in cycles:
                    cycles.append(cycle)
                return
            
            if node_id in visited:
                return
            
            if node_id not in episode.nodes:
                return
            
            visited.add(node_id)
            path.append(node_id)
            path_set.add(node_id)
            
            node = episode.nodes[node_id]
            
            # Checking all outgoing links
            if node.next_node_default:
                dfs(node.next_node_default, path_set)
            
            for choice in node.choices:
                if isinstance(choice, dict):
                    goto = choice.get('goto')
                    if goto:
                        dfs(goto, path_set)
                elif hasattr(choice, 'goto') and choice.goto:
                    dfs(choice.goto, path_set)
            
            path.pop()
            path_set.remove(node_id)
        
        # Run DFS from each node
        for node_id in episode.nodes.keys():
            dfs(node_id, set())
        
        return cycles
    
    def _log(self, message: str):
        """Logs debug message"""
        if self.debug:
            print(f"[LinkValidator] {message}")


__all__ = ['LinkValidator']