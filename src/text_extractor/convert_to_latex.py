"""
Standalone script to convert JSON files to LaTeX format.

Usage:
    python convert_to_latex.py
"""

from extraction import json_to_latex_syllabus, json_to_latex_notes
from pathlib import Path
import sys

# Set UTF-8 encoding for console output
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def main():
    """Convert JSON files to LaTeX format."""
    print("JSON to LaTeX Converter")
    print("=" * 50)
    
    output_dir = Path("output")
    if not output_dir.exists():
        print(f"[ERROR] Output directory not found: {output_dir}")
        print("Please run extraction.py first to generate JSON files.")
        return
    
    # Convert syllabus
    syllabus_json = output_dir / "syllabus.json"
    if syllabus_json.exists():
        print("\nConverting syllabus.json to LaTeX...")
        json_to_latex_syllabus(
            str(syllabus_json),
            str(output_dir / "syllabus.tex")
        )
        print(f"[OK] Created: {output_dir / 'syllabus.tex'}")
    else:
        print(f"[WARNING] Syllabus JSON not found: {syllabus_json}")
    
    # Convert notes
    notes_json = output_dir / "notes.json"
    if notes_json.exists():
        print("\nConverting notes.json to LaTeX...")
        json_to_latex_notes(
            str(notes_json),
            str(output_dir / "notes.tex")
        )
        print(f"[OK] Created: {output_dir / 'notes.tex'}")
    else:
        print(f"[WARNING] Notes JSON not found: {notes_json}")
    
    print("\n" + "=" * 50)
    print("Conversion complete!")
    print("\nTo compile the LaTeX files, run:")
    print("  pdflatex output/syllabus.tex")
    print("  pdflatex output/notes.tex")


if __name__ == "__main__":
    main()

