#!/usr/bin/env python3
"""
Demo script showing how to use Manim-MCP
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.syllabus_generator import convert_json_to_syllabus, SyllabusGenerator
import json


def demo_basic_usage():
    """Demo 1: Basic usage without AI"""
    print("=" * 60)
    print("DEMO 1: Basic Syllabus Generation (No AI)")
    print("=" * 60)
    
    syllabus = convert_json_to_syllabus(
        'examples/example_input.json',
        output_path='output/demo_basic.md',
        use_professor=False
    )
    
    print(f"✅ Generated {len(syllabus)} characters")
    print("\nFirst 300 characters:")
    print(syllabus[:300])
    print("...")


def demo_with_class():
    """Demo 2: Using the SyllabusGenerator class"""
    print("\n" + "=" * 60)
    print("DEMO 2: Using SyllabusGenerator Class")
    print("=" * 60)
    
    # Load JSON
    with open('examples/example_input.json') as f:
        data = json.load(f)
    
    # Create generator
    generator = SyllabusGenerator(data, use_professor=False)
    
    print(f"Document type: {generator.document_type}")
    print(f"Number of sections: {len(generator.sections)}")
    print(f"Topics: {', '.join(generator.index)}")
    
    # Generate
    syllabus = generator.generate_syllabus()
    generator.save_to_file('output/demo_class.md')
    
    print(f"✅ Generated and saved to output/demo_class.md")


def demo_custom_json():
    """Demo 3: Create custom JSON and generate"""
    print("\n" + "=" * 60)
    print("DEMO 3: Custom JSON Content")
    print("=" * 60)
    
    # Create custom JSON
    custom_data = {
        "document_type": "lecture_notes",
        "index": ["Introduction", "Equations", "Conclusion"],
        "sections": [
            {
                "id": 0,
                "title": "Introduction",
                "content": "Welcome to calculus!"
            },
            {
                "id": 1,
                "title": "Equations",
                "content": {
                    "derivative": "dy/dx",
                    "integral": "∫ f(x) dx"
                }
            },
            {
                "id": 2,
                "title": "Conclusion",
                "content": ["Remember the fundamentals", "Practice daily", "Ask questions"]
            }
        ]
    }
    
    # Generate
    generator = SyllabusGenerator(custom_data, use_professor=False)
    syllabus = generator.generate_syllabus()
    generator.save_to_file('output/demo_custom.md')
    
    print(f"✅ Generated custom syllabus")
    print("\nTable of Contents:")
    print("  1. Introduction")
    print("  2. Equations")
    print("  3. Conclusion")


def demo_ai_enhanced():
    """Demo 4: AI-enhanced generation (requires API key)"""
    print("\n" + "=" * 60)
    print("DEMO 4: AI-Enhanced Generation")
    print("=" * 60)
    
    import os
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OPENAI_API_KEY not set - skipping AI demo")
        print("   Set your API key to try AI enhancement:")
        print("   export OPENAI_API_KEY='your-key'")
        return
    
    print("🤖 Using AI Professor to enhance content...")
    
    try:
        syllabus = convert_json_to_syllabus(
            'examples/example_input.json',
            output_path='output/demo_ai.md',
            use_professor=True
        )
        
        print(f"✅ Generated AI-enhanced syllabus ({len(syllabus)} chars)")
        print("   Includes:")
        print("   - Detailed explanations")
        print("   - LaTeX equations")
        print("   - Animation suggestions")
        print("   - Pacing notes")
        
    except Exception as e:
        print(f"❌ AI enhancement failed: {e}")
        print("   (This is expected if API key is invalid)")


def main():
    """Run all demos"""
    print("\n🎓 Manim-MCP Demo Script\n")
    
    # Ensure output directory exists
    Path('output').mkdir(exist_ok=True)
    
    # Run demos
    demo_basic_usage()
    demo_with_class()
    demo_custom_json()
    demo_ai_enhanced()
    
    print("\n" + "=" * 60)
    print("All demos complete!")
    print("=" * 60)
    print("\nGenerated files in output/:")
    print("  - demo_basic.md")
    print("  - demo_class.md")
    print("  - demo_custom.md")
    print("  - demo_ai.md (if AI enabled)")
    print("\nNext: Try 'python main.py examples/example_input.json'")
    print()


if __name__ == "__main__":
    main()

