#!/usr/bin/env python3
"""
Main entry point for Manim-MCP Syllabus Generator
"""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.syllabus_generator import convert_json_to_syllabus
from utils.config_loader import load_config


def main():
    parser = argparse.ArgumentParser(
        description="Convert JSON to AI-enhanced teaching syllabus for Manim animations"
    )
    
    parser.add_argument(
        "input",
        help="Path to input JSON file"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Path to output file (default: output/syllabus.md)",
        default="output/syllabus.md"
    )
    
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable AI professor enhancement (faster, basic output)"
    )
    
    parser.add_argument(
        "--config",
        help="Path to config file (default: config/config.yaml)",
        default=None
    )
    
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
        default=None
    )
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"🎓 Manim-MCP Syllabus Generator")
    print(f"   Input: {args.input}")
    print(f"   Output: {args.output}")
    print(f"   AI Enhancement: {'Disabled' if args.no_ai else 'Enabled'}")
    print()
    
    try:
        # Generate syllabus
        syllabus = convert_json_to_syllabus(
            args.input,
            output_path=args.output,
            use_professor=not args.no_ai,
            config_path=args.config,
            api_key=args.api_key
        )
        
        print()
        print("✅ Syllabus generated successfully!")
        print(f"   View at: {args.output}")
        
    except FileNotFoundError as e:
        print(f"❌ Error: File not found - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

