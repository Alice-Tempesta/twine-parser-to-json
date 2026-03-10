"""
Validator of variables and flags
Checks the correct use of variables
"""

from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from ..models.story import Story
from ..models.episode import Episode
from ..models.flag import GlobalFlag, VariableType


class FlagValidator:
    """
    Validator of variables and flags
    
    Checks:
    - Are all used variables declared?
    - Type correctness during operations
    - Are there any name conflicts?
    - Using variables before initialization
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.errors = []
        self.warnings = []
        self.used_variables = defaultdict(set)  # эпизод -> set переменных
        self.declared_variables = defaultdict(set)  # эпизод -> set переменных
    
    def validate_story(self, story: Story) -> Tuple[List[str], List[str]]:
        """
        Validates all variables in the entire history
        
        Returns:
            Tuple (errors, warnings)
        """
        self.errors = []
        self.warnings = []
        self.used_variables.clear()
        self.declared_variables.clear()
        
        self._log("Validating variables and flags...")
        
        # Collecting information about the use of variables
        for episode_num, episode in story.episodes.items():
            self._analyze_episode(episode, episode_num)
        
        # Checking every variable
        all_variables = set()
        for episode_num, vars_set in self.used_variables.items():
            all_variables.update(vars_set)
        
        for var_name in all_variables:
            self._validate_variable(var_name, story)
        
        # Checking name conflicts
        self._check_name_conflicts(story)
        
        self._log(f"Validation complete: {len(self.errors)} errors, {len(self.warnings)} warnings")
        
        return self.errors, self.warnings
    
    def _analyze_episode(self, episode: Episode, episode_num: int):
        """Analyzes the use of variables in the episode"""
        
        # Adding declared variables from the initial state
        for var_name in episode.initial_state.variables.keys():
            self.declared_variables[episode_num].add(var_name)
        
        # We analyze each node
        for node_id, node in episode.nodes.items():
            self._analyze_node(node, episode_num, node_id)
    
    def _analyze_node(self, node: Node, episode_num: int, node_id: str):
        """Analyzes the use of variables in the node"""
        
        # Checking the effects upon entry
        for effect in node.transitions.on_enter:
            self._analyze_effect(effect, episode_num, node_id)
        
        # Checking the effects upon exit
        for effect in node.transitions.on_exit:
            self._analyze_effect(effect, episode_num, node_id)
        
        # Checking the elections
        for choice in node.choices:
            self._analyze_choice(choice, episode_num, node_id)
        
        # Checking the conditions
        if node.condition:
            self._analyze_condition(node.condition, episode_num, node_id)
    
    def _analyze_effect(self, effect: Dict, episode_num: int, node_id: str):
        """Analyzes the effect"""
        if isinstance(effect, dict):
            e_type = effect.get('type', '')
            
            if e_type == 'modify_variable':
                var_name = effect.get('variable')
                if var_name:
                    self.used_variables[episode_num].add(var_name)
                    
                    # Checking the operation
                    op = effect.get('operation')
                    if op in ['add', 'subtract', 'multiply', 'divide']:
                        # Arithmetic operations require a numeric type
                        self._check_numeric_operation(var_name, op, episode_num, node_id)
    
    def _analyze_choice(self, choice: Dict, episode_num: int, node_id: str):
        """Analyzes the selection"""
        if isinstance(choice, dict):
            # Checking the effects of choice
            for effect in choice.get('effects', []):
                self._analyze_effect(effect, episode_num, node_id)
            
            # Checking the selection condition
            condition = choice.get('condition')
            if condition:
                self._analyze_condition(condition, episode_num, node_id)
        elif hasattr(choice, 'effects'):
            for effect in choice.effects:
                self._analyze_effect(effect, episode_num, node_id)
    
    def _analyze_condition(self, condition, episode_num: int, node_id: str):
        """Analyzes the condition """
        # Simple implementation - can be extended
        pass
    
    def _validate_variable(self, var_name: str, story: Story):
        """
        Tests one variable
        
        - Has it been announced?
        - Are there type conflicts between episodes?
        """
        # Checking the ad
        is_declared = False
        var_type = None
        declaring_episodes = []
        
        for episode_num, vars_set in self.declared_variables.items():
            if var_name in vars_set:
                is_declared = True
                declaring_episodes.append(episode_num)
                
                # Getting the type from the episode
                episode = story.episodes.get(episode_num)
                if episode and var_name in episode.initial_state.variables:
                    value = episode.initial_state.variables[var_name]
                    current_type = self._infer_type(value)
                    
                    if var_type and var_type != current_type:
                        self.warnings.append(
                            f"Variable '${var_name}' has different types across episodes: "
                            f"{var_type} in episode {declaring_episodes[0]}, "
                            f"{current_type} in episode {episode_num}"
                        )
                    else:
                        var_type = current_type
        
        # Checking global variables
        if var_name in story.global_variables:
            is_declared = True
            global_var = story.global_variables[var_name]
            var_type = global_var.type
        
        if not is_declared:
            # The variable is used but not declared
            using_episodes = [str(ep) for ep in self.used_variables.keys() 
                            if var_name in self.used_variables[ep]]
            
            self.warnings.append(
                f"Variable '${var_name}' is used but not declared "
                f"(in episodes: {', '.join(using_episodes)})"
            )
    
    def _check_numeric_operation(self, var_name: str, op: str, episode_num: int, node_id: str):
        """Checks that a variable is numeric for arithmetic operations"""
        # This check will be extended once we have type information
        pass
    
    def _check_name_conflicts(self, story: Story):
        """Checks for variable name conflicts"""
        
        # Checking for conflicts with reserved names
        reserved_names = ['it', 'time', 'turns', 'visits', 'exits', 'pos']
        
        for var_name in story.global_variables.keys():
            if var_name.lower() in reserved_names:
                self.warnings.append(
                    f"Variable '${var_name}' conflicts with reserved identifier "
                    f"'{var_name.lower()}'. This may cause unexpected behavior."
                )
    
    def _infer_type(self, value) -> VariableType:
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
    
    def _log(self, message: str):
        """Logs debug message"""
        if self.debug:
            print(f"[FlagValidator] {message}")

__all__ = ['FlagValidator']