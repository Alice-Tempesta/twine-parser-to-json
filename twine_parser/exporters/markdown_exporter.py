"""
Markdown exporter
Creates a readable report for scriptwriters and documentation
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from ..models.story import Story
from ..models.episode import Episode
from ..models.node import Node, NodeType, ContentType


class MarkdownExporter:
    """
    Markdown Exporter

    Creates a readable report with the game's structure:
    - Table of Contents
    - Episode Information
    - All Content Nodes
    - Connection Diagram
    - Statistics
    """
    
    def __init__(self, output_dir: str, debug: bool = False):
        self.output_dir = Path(output_dir)
        self.debug = debug
        
        # Create a directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export(self, story: Story, filename: str = "story_report.md") -> str:
        """
        Exports history to a Markdown report.

        Args:
        story: History object
        filename: Report file name

        Returns:
        Path to the created file
        """
        filepath = self.output_dir / filename
        
        # Generating content
        content = self._generate_report(story)
        
        # Save
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self._log(f"Exported markdown report: {filename}")
        
        return str(filepath)
    
    def _generate_report(self, story: Story) -> str:
        """Generates a complete report"""
        lines = []
        
        # Heading
        lines.append(f"# 📖 {story.metadata.title}")
        lines.append()
        
        # Metadata
        lines.append("## Metadata")
        lines.append()
        lines.append(f"- **Author:** {story.metadata.author}")
        lines.append(f"- **Version:** {story.metadata.version}")
        lines.append(f"- **Created:** {story.metadata.created}")
        lines.append(f"- **Changed:** {story.metadata.last_modified}")
        if story.metadata.ifid:
            lines.append(f"- **IFID:** `{story.metadata.ifid}`")
        if story.metadata.description:
            lines.append(f"- **Description:** {story.metadata.description}")
        lines.append()
        
        # Statistics
        stats = story.get_stats()
        lines.append("## Statistics")
        lines.append()
        lines.append(f"- **Episodes:** {stats.total_episodes}")
        lines.append(f"- **Total nodes:** {stats.total_nodes}")
        lines.append(f"- **Options to choose from:** {stats.total_choices}")
        lines.append(f"- **Investigation points:** {stats.total_investigation_points}")
        lines.append()
        
        # Global Variables
        if story.global_variables:
            lines.append("## Global variables")
            lines.append()
            lines.append("| Name | Type | Meaning | Description |")
            lines.append("|------|------|---------|-------------|")
            
            for name, var in story.global_variables.items():
                lines.append(f"| `${name}` | {var.type.value} | `{var.value}` | {var.description or ''} |")
            lines.append()
        
        # Episode table of contents
        lines.append("## Episodes")
        lines.append()
        
        for episode_num, episode in story.episodes.items():
            lines.append(f"### Episode {episode_num}: {episode.metadata.title}")
            lines.append()
            lines.append(f"*{episode.metadata.description}*")
            lines.append()
            lines.append(f"- **Cover:** `{episode.metadata.cover}`")
            lines.append(f"- **Cost of energy:** {episode.metadata.energy_cost}")
            if episode.metadata.required_episode:
                lines.append(f"- **Episode required:** {episode.metadata.required_episode}")
            lines.append(f"- **Total nodes:** {len(episode.nodes)}")
            lines.append(f"- **Стартовая нода:** `{episode.start_node}`")
            lines.append()
            
            # Connection diagram
            lines.append(self._generate_flowchart(episode))
            lines.append()
            
            # All episode nodes
            lines.append(self._generate_episode_nodes(episode))
            lines.append()
        
        return "\n".join(lines)
    
    def _generate_episode_nodes(self, episode: Episode) -> str:
        """Generates a description of all nodes of the episode"""
        lines = ["#### Episode nodes:", ""]
        
        # We sort nodes by name for convenience
        sorted_nodes = sorted(episode.nodes.items(), key=lambda x: x[0])
        
        for node_id, node in sorted_nodes:
            lines.append(self._generate_node_description(node, episode))
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_node_description(self, node: Node, episode: Episode) -> str:
        """Generates a description of one node"""
        lines = []
        
        # Node header
        node_type_emoji = {
            NodeType.CUTSCENE: "🎬",
            NodeType.DIALOGUE: "💬",
            NodeType.DIALOGUE_WITH_CHOICES: "🎭",
            NodeType.INVESTIGATION: "🔍",
            NodeType.CHARACTER_CREATOR: "🎨",
            NodeType.EPISODE_END: "🏁"
        }
        emoji = node_type_emoji.get(node.type, "📄")
        
        title_part = f" {node.title}" if node.title else ""
        lines.append(f"##### {emoji} `{node.id}`{title_part}")
        
        # Metadata nodes
        if node.hidden:
            lines.append("*🔒 Hidden node*")
        
        if node.media.get('background'):
            lines.append(f"- **Background:** `{node.media['background']}`")
        if node.media.get('music'):
            lines.append(f"- **Music:** `{node.media['music']}`")
        if node.media.get('sounds'):
            sounds = node.media['sounds']
            if isinstance(sounds, list):
                lines.append(f"- **Sounds:** {len(sounds)}")
        
        # Characters
        if node.characters_on_scene:
            chars = []
            for char in node.characters_on_scene:
                if isinstance(char, dict):
                    chars.append(f"`{char.get('id', 'unknown')}`")
                else:
                    chars.append(f"`{char.id}`")
            lines.append(f"- **Characters:** {', '.join(chars)}")
        
        lines.append("")
        
        # Content
        if node.content:
            lines.append("**Content:**")
            for item in node.content:
                lines.append(self._format_content_item(item))
            lines.append("")
        
        # Elections
        if node.choices:
            lines.append("**Choice options:**")
            for choice in node.choices:
                lines.append(self._format_choice(choice, episode))
            lines.append("")
        
        # Investigation points
        if node.investigation_points:
            lines.append("**Investigation points:**")
            for point in node.investigation_points:
                lines.append(self._format_investigation_point(point))
            lines.append("")
        
        # Transitions
        if node.next_node_default:
            target = node.next_node_default
            target_title = self._get_node_title(target, episode)
            lines.append(f"**→ Next node:** `{target}` {target_title}")
        
        if node.condition:
            lines.append(f"**→ Conditional jump:** `{node.condition.condition}`")
            lines.append(f"  - If true: `{node.condition.then}`")
            if node.condition.else_:
                lines.append(f"  - If false: `{node.condition.else_}`")
        
        # Effects
        if node.transitions.on_enter:
            lines.append("**Entry effects:**")
            for effect in node.transitions.on_enter:
                lines.append(f"  - {self._format_effect(effect)}")
        
        if node.transitions.on_exit:
            lines.append("**Exit effects:**")
            for effect in node.transitions.on_exit:
                lines.append(f"  - {self._format_effect(effect)}")
        
        lines.append("")
        
        return "\n".join(lines)
    
    def _format_content_item(self, item: Any) -> str:
        """Formats a content element"""
        if isinstance(item, dict):
            item_type = item.get('type', 'unknown')
            if item_type == 'dialogue':
                speaker = item.get('speaker', '???')
                text = item.get('text', '')
                return f"  - **{speaker}:** {text}"
            elif item_type == 'narration':
                return f"  - *{item.get('text', '')}*"
            elif item_type == 'action':
                return f"  - _{item.get('description', '')}_"
            elif item_type == 'sound':
                return f"  - 🔊 `{item.get('file', '')}`"
            elif item_type == 'custom':
                return f"  - 🧩 {item.get('text', '')}"
            else:
                return f"  - {item}"
        else:
            return f"  - {item}"
    
    def _format_choice(self, choice: Any, episode: Episode) -> str:
        """Formats the selection option"""
        if isinstance(choice, dict):
            text = choice.get('text', '')
            goto = choice.get('goto')
            
            # Checking the existence of the target node
            goto_text = ""
            if goto:
                target_title = self._get_node_title(goto, episode)
                goto_text = f" → `{goto}` {target_title}"
            
            # Effects
            effects = choice.get('effects', [])
            effects_text = ""
            if effects:
                effects_list = [self._format_effect(e) for e in effects]
                effects_text = f" [{', '.join(effects_list)}]"
            
            # Conditions
            condition = choice.get('condition')
            condition_text = f" (if: {condition})" if condition else ""
            
            return f"  - **{text}**{goto_text}{effects_text}{condition_text}"
        else:
            return f"  - {choice}"
    
    def _format_investigation_point(self, point: Any) -> str:
        """Formats the investigation point"""
        if isinstance(point, dict):
            name = point.get('name', '')
            desc = point.get('description', '')
            skill = point.get('required_skill', '')
            skill_val = point.get('required_skill_value', '')
            
            result = f"  - **{name}:** {desc}"
            if skill:
                result += f" (required: {skill} {skill_val})"
            return result
        else:
            return f"  - {point}"
    
    def _format_effect(self, effect: Any) -> str:
        """Formats the  effect """
        if isinstance(effect, dict):
            e_type = effect.get('type', '')
            
            if e_type == 'modify_variable':
                var = effect.get('variable', '')
                op = effect.get('operation', '')
                val = effect.get('value', '')
                return f"${var} {op} {val}"
            
            elif e_type == 'add_item':
                item = effect.get('item', '')
                qty = effect.get('quantity', 1)
                return f"+ {item} x{qty}"
            
            elif e_type == 'remove_item':
                item = effect.get('item', '')
                qty = effect.get('quantity', 1)
                return f"- {item} x{qty}"
            
            elif e_type == 'cost':
                currency = effect.get('currency', 'soft')
                amount = effect.get('amount', 0)
                return f"-{amount} {currency}"
            
            else:
                return str(effect)
        else:
            return str(effect)
    
    def _generate_flowchart(self, episode: Episode) -> str:
        """Generates a diagram of connections between nodes in the Mermaid  format"""
        lines = ["```mermaid", "graph TD;"]
        
        # Adding all nodes
        for node_id, node in episode.nodes.items():
            # Escaping special characters
            safe_id = node_id.replace('-', '_').replace(' ', '_')
            label = node.title if node.title else node_id[:20]
            lines.append(f"    {safe_id}[\"{label}\"];")
        
        lines.append("")
        
        # Adding connections
        for node_id, node in episode.nodes.items():
            safe_id = node_id.replace('-', '_').replace(' ', '_')
            
            # Normal transition
            if node.next_node_default:
                target = node.next_node_default.replace('-', '_').replace(' ', '_')
                lines.append(f"    {safe_id} --> {target};")
            
            # Transitions from elections
            for choice in node.choices:
                if isinstance(choice, dict) and choice.get('goto'):
                    goto = choice['goto'].replace('-', '_').replace(' ', '_')
                    lines.append(f"    {safe_id} -.-> {goto};")
        
        lines.append("```")
        
        return "\n".join(lines)
    
    def _get_node_title(self, node_id: str, episode: Episode) -> str:
        """Returns the node title for beautiful display"""
        node = episode.nodes.get(node_id)
        if node and node.title:
            return f"*{node.title}*"
        return ""
    
    def _log(self, message: str):
        """Logs debug message"""
        if self.debug:
            print(f"[MarkdownExporter] {message}")

__all__ = ['MarkdownExporter']