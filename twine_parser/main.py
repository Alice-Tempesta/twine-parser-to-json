#!/usr/bin/env python3
"""
Twine to Game Engine JSON Parser
Converts Twine HTML files to structured JSON for the game engine

Usage:
    python -m twine_parser.main input.html -o output_dir --debug
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add the parent directory to the import path
sys.path.insert(0, str(Path(__file__).parent.parent))

from twine_parser.config import ParserConfig
from twine_parser.parsers.html_parser import HTMLParser
from twine_parser.parsers.metadata_parser import MetadataParser
from twine_parser.builders.story_builder import StoryBuilder
from twine_parser.validators.link_validator import LinkValidator
from twine_parser.validators.flag_validator import FlagValidator
from twine_parser.validators.episode_validator import EpisodeValidator
from twine_parser.exporters.json_exporter import JSONExporter
from twine_parser.exporters.markdown_exporter import MarkdownExporter


class TwineParserApp:
    """
    Twine parser main application
    Combines all components into a single workflow
    """
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.start_time = None
        self.story = None
        
        # Components
        self.html_parser = HTMLParser()
        self.story_builder = StoryBuilder(debug=config.debug)
        self.link_validator = LinkValidator(debug=config.debug)
        self.flag_validator = FlagValidator(debug=config.debug)
        self.episode_validator = EpisodeValidator(debug=config.debug)
        self.json_exporter = JSONExporter(
            output_dir=config.output_dir,
            pretty=config.pretty_json,
            split_episodes=config.split_by_episodes,
            debug=config.debug
        )
        self.markdown_exporter = MarkdownExporter(
            output_dir=config.output_dir,
            debug=config.debug
        )
    
    def run(self) -> int:
        """
        Starts the parsing process
        
        Returns:
            0 on success, 1 on error
        """
        import time
        self.start_time = time.time()
        
        self._print_header()
        
        # Step 1: Read the file
        if not self._read_input_file():
            return 1
        
        # Step 2: Parsing HTML
        if not self._parse_html():
            return 1
        
        # Step 3: Building a Story
        if not self._build_story():
            return 1
        
        # Step 4: Validation
        if not self._validate():
            return 1
        
        # Step 5: Export
        if not self._export():
            return 1
        
        # Step 6: Report
        self._print_summary()
        
        return 0
    
    def _read_input_file(self) -> bool:
        """Reads the input file"""
        self._print_step(1, "Reading input file")
        
        input_path = Path(self.config.input_file)
        if not input_path.exists():
            self._error(f"Input file not found: {input_path}")
            return False
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            
            self._success(f"Read {len(self.content)} bytes from {input_path.name}")
            return True
            
        except Exception as e:
            self._error(f"Failed to read input file: {e}")
            return False
    
    def _parse_html(self) -> bool:
        """Parse HTML file"""
        self._print_step(2, "Parsing HTML")
        
        try:
            # Parse HTML
            self.html_data = self.html_parser.parse_content(self.content)
            
            passages = self.html_data['passages']
            story_name = self.html_data['story_name']
            
            self._success(f"Found {len(passages)} passages")
            
            if self.config.debug:
                print(f"  Story name: {story_name}")
                print(f"  Start node PID: {self.html_data.get('startnode')}")
                print(f"  IFID: {self.html_data.get('ifid')}")
                print(f"  Format: {self.html_data.get('format')} v{self.html_data.get('format_version')}")
                print(f"  Styles: {len(self.html_data.get('styles', []))}")
                print(f"  Scripts: {len(self.html_data.get('scripts', []))}")
            
            return True
            
        except Exception as e:
            self._error(f"Failed to parse HTML: {e}")
            if self.config.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def _build_story(self) -> bool:
        """Builds a story from passages"""
        self._print_step(3, "Building story structure")
        
        try:
            self.story = self.story_builder.build(
                self.html_data['passages'],
                self.html_data
            )
            
            if not self.story:
                self._error("Failed to build story")
                return False
            
            stats = self.story.get_stats()
            self._success(
                f"Built story: {stats.total_episodes} episodes, "
                f"{stats.total_nodes} nodes"
            )
            
            # Showing collector warnings
            for warning in self.story_builder.get_warnings():
                self._warning(warning)
            
            return True
            
        except Exception as e:
            self._error(f"Failed to build story: {e}")
            if self.config.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def _validate(self) -> bool:
        """Validates history"""
        if not self.config.validate:
            self._print_step(4, "Validation skipped")
            return True
        
        self._print_step(4, "Validating story")
        
        all_errors = []
        all_warnings = []
        
        # Link Validation
        if self.config.check_links:
            errors, warnings = self.link_validator.validate_story(self.story)
            all_errors.extend(errors)
            all_warnings.extend(warnings)
        
        # Variable Validation
        if self.config.check_variables:
            errors, warnings = self.flag_validator.validate_story(self.story)
            all_errors.extend(errors)
            all_warnings.extend(warnings)
        
        # Episode Validation
        errors, warnings = self.episode_validator.validate_story(self.story)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        
        # We display the results
        if all_errors:
            self._error(f"Found {len(all_errors)} errors:")
            for error in all_errors[:10]:  # show the first 10
                print(f"  • {error}")
            if len(all_errors) > 10:
                print(f"  ... and {len(all_errors) - 10} more errors")
            
            if self.config.strict_validation:
                return False
        else:
            self._success("No errors found")
        
        if all_warnings:
            self._warning(f"Found {len(all_warnings)} warnings:")
            for warning in all_warnings[:5]:  # show the first 5
                print(f"  • {warning}")
            if len(all_warnings) > 5:
                print(f"  ... and {len(all_warnings) - 5} more warnings")
        
        return True
    
    def _export(self) -> bool:
        """Exports history"""
        self._print_step(5, "Exporting story")
        
        try:
            # Export to JSON
            json_files = self.json_exporter.export(self.story)
            self._success(f"Exported {len(json_files)} JSON files")
            
            if self.config.debug:
                for file in json_files[:5]:
                    print(f"  • {Path(file).name}")
                if len(json_files) > 5:
                    print(f"  • ... and {len(json_files) - 5} more")
            
            # Export to Markdown report
            try:
                md_file = self.markdown_exporter.export(self.story)
                self._success(f"Exported Markdown report: {Path(md_file).name}")
            except Exception as e:
                self._warning(f"Failed to export Markdown report: {e}")
            
            return True
            
        except Exception as e:
            self._error(f"Failed to export story: {e}")
            if self.config.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def _print_header(self):
        """Prints the title"""
        print("\n" + "="*60)
        print(" Twine to Game Engine JSON Parser")
        print("="*60)
        print(f"Input:  {self.config.input_file}")
        print(f"Output: {self.config.output_dir}")
        print("-"*60)
    
    def _print_step(self, step: int, message: str):
        """Prints the execution step"""
        print(f"\n Step {step}: {message}")
    
    def _print_summary(self):
        """Prints the final report"""
        import time
        elapsed = time.time() - self.start_time
        
        print("\n" + "="*60)
        print("  Parsing completed successfully! <3")
        print("="*60)
        
        if self.story:
            stats = self.story.get_stats()
            print(f"\n Summary:")
            print(f"  • Episodes:    {stats.total_episodes}")
            print(f"  • Total nodes: {stats.total_nodes}")
            print(f"  • Choices:     {stats.total_choices}")
            print(f"  • Invest points: {stats.total_investigation_points}")
        
        print(f"\n⏱Time: {elapsed:.2f} seconds")
        print(f"Output: {os.path.abspath(self.config.output_dir)}")
        print("="*60 + "\n")
    
    def _success(self, message: str):
        """Prints a success message"""
        print(f"  ✅ {message}")
    
    def _error(self, message: str):
        """Prints an error message """
        print(f"  ERROR {message}")
    
    def _warning(self, message: str):
        """Prints a warning"""
        print(f"  !!WARNING!!  {message}")


def create_parser() -> argparse.ArgumentParser:
    """Creates a command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Twine to Game Engine JSON Parser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m twine_parser.main story.html -o output
  python -m twine_parser.main story.html --debug --validate
  python -m twine_parser.main story.html --pretty --no-split
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Path to input HTML file'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='Output directory (default: output)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        default=True,
        help='Validate the story (default: True)'
    )
    
    parser.add_argument(
        '--no-validate',
        action='store_false',
        dest='validate',
        help='Skip validation'
    )
    
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Stop on validation errors'
    )
    
    parser.add_argument(
        '--pretty',
        action='store_true',
        default=True,
        help='Pretty print JSON (default: True)'
    )
    
    parser.add_argument(
        '--minify',
        action='store_false',
        dest='pretty',
        help='Minify JSON output'
    )
    
    parser.add_argument(
        '--split',
        action='store_true',
        default=True,
        help='Split episodes into separate files (default: True)'
    )
    
    parser.add_argument(
        '--no-split',
        action='store_false',
        dest='split',
        help='Export all episodes to a single file'
    )
    
    parser.add_argument(
        '--check-links',
        action='store_true',
        default=True,
        help='Check for broken links (default: True)'
    )
    
    parser.add_argument(
        '--no-check-links',
        action='store_false',
        dest='check_links',
        help='Skip link validation'
    )
    
    parser.add_argument(
        '--check-vars',
        action='store_true',
        default=True,
        help='Check variables usage (default: True)'
    )
    
    parser.add_argument(
        '--no-check-vars',
        action='store_false',
        dest='check_vars',
        help='Skip variable validation'
    )
    
    return parser


def main():
    """Entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Creating a configuration
    config = ParserConfig(
        input_file=args.input_file,
        output_dir=args.output,
        debug=args.debug,
        validate=args.validate,
        strict_validation=args.strict,
        pretty_json=args.pretty,
        split_by_episodes=args.split,
        check_links=args.check_links,
        check_variables=args.check_vars
    )
    
    # Launch the application
    app = TwineParserApp(config)
    exit_code = app.run()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()