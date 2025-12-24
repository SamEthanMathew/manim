"""
LEGACY FILE - PROJECT HAS BEEN REORGANIZED

This file has been moved and refactored.

New location: src/core/syllabus_generator.py

To use the new structure:

    from src.core.syllabus_generator import convert_json_to_syllabus

Or use the CLI:

    python main.py input.json -o output.md

See README.md for complete documentation.
"""

import sys
from pathlib import Path

# Add src to path and import from new location
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from core.syllabus_generator import convert_json_to_syllabus, SyllabusGenerator
    
    print("⚠️  WARNING: You're importing from the legacy json_to_syllabus.py file.")
    print("   This file is for backward compatibility only.")
    print("   Please update your imports to:")
    print("   from src.core.syllabus_generator import convert_json_to_syllabus")
    print()
    
    # Re-export for backward compatibility
    __all__ = ['convert_json_to_syllabus', 'SyllabusGenerator']
    
except ImportError as e:
    print(f"Error: Could not import from new structure: {e}")
    print("Please see README.md for setup instructions.")
    sys.exit(1)
