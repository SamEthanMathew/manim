# PDF Extraction System for Manim Integration

A flexible PDF extraction system using pdfplumber that automatically detects document structure and exports hierarchical JSON data for syllabus and notes PDFs.

## Features

- **Automatic Structure Detection**: Identifies headings and sections using font analysis, positioning, and pattern recognition
- **Hierarchical Output**: Generates nested JSON structures with automatic indexing
- **Adaptive Processing**: Works with different PDF structures and formatting styles
- **Table Extraction**: Preserves table data (useful for schedules, grading policies)
- **Multiple Detection Strategies**:
  - Font-based: Identifies headings by font size and weight
  - Position-based: Detects sections by alignment and spacing
  - Pattern-based: Recognizes numbered sections, ALL CAPS, and title case headings

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

Run the extraction script directly to process both test PDFs:

```bash
python extraction.py
```

This will:
- Extract the syllabus from `testfiles/DiscreteMath_Syllabus.pdf`
- Extract the notes from `testfiles/DiscreteMath_Combinatronics.pdf`
- Save JSON outputs to the `output/` directory
- Convert JSON files to LaTeX format (`.tex` files)

### Programmatic Usage

#### Extract Syllabus

```python
from extraction import extract_syllabus

# Extract syllabus
syllabus_data = extract_syllabus(
    "testfiles/DiscreteMath_Syllabus.pdf",
    "output/syllabus.json"
)

# Access the data
print(f"Sections: {syllabus_data['index']}")
for section in syllabus_data['sections']:
    print(f"- {section['title']}")
```

#### Extract Notes

```python
from extraction import extract_notes

# Extract notes
notes_data = extract_notes(
    "testfiles/DiscreteMath_Combinatronics.pdf",
    "output/notes.json"
)

# Access the data
print(f"Main Topic: {notes_data['main_topic']}")
print(f"Sections: {notes_data['index']}")
```

#### Custom Extraction

```python
from extraction import SyllabusExtractor, NotesExtractor

# Use context manager for custom processing
with SyllabusExtractor("path/to/syllabus.pdf") as extractor:
    # Get formatted text
    formatted = extractor.extract_text_with_formatting()
    
    # Extract with custom output path
    data = extractor.extract("custom/output/path.json")
```

### LaTeX Conversion

Convert extracted JSON data back to LaTeX format:

```python
from extraction import json_to_latex_syllabus, json_to_latex_notes

# Convert syllabus JSON to LaTeX
json_to_latex_syllabus(
    "output/syllabus.json",
    "output/syllabus.tex"
)

# Convert notes JSON to LaTeX
json_to_latex_notes(
    "output/notes.json",
    "output/notes.tex"
)

# Custom conversion without preamble (content only)
json_to_latex_notes(
    "output/notes.json",
    "output/notes_content.tex",
    include_preamble=False  # Only section content, no \documentclass, etc.
)
```

The generated LaTeX files include:
- Complete document structure with `\documentclass`
- Math packages (`amsmath`, `amssymb`, `amsthm`)
- Automatic table of contents
- Properly escaped special characters
- Hierarchical sections and subsections
- Tables converted to `tabular` environments

#### Standalone LaTeX Converter

You can also use the standalone conversion script:

```bash
python convert_to_latex.py
```

This will convert any existing JSON files in the `output/` directory to LaTeX format.

## Output Format

### Syllabus JSON Structure

```json
{
  "document_type": "syllabus",
  "metadata": {
    "filename": "DiscreteMath_Syllabus.pdf",
    "num_pages": 5
  },
  "index": [
    "Course Information",
    "Topics Covered",
    "Grading Policy",
    "Schedule"
  ],
  "sections": [
    {
      "id": 0,
      "title": "Course Information",
      "level": 1,
      "content": "...",
      "page_start": 1,
      "page_end": 1,
      "confidence": 0.9,
      "subsections": [...]
    }
  ],
  "tables": [
    {
      "page": 2,
      "data": [[...]]
    }
  ]
}
```

### Notes JSON Structure

```json
{
  "document_type": "notes",
  "main_topic": "Discrete Math - Combinatorics",
  "metadata": {
    "filename": "DiscreteMath_Combinatronics.pdf",
    "num_pages": 15
  },
  "index": [
    "Introduction",
    "Permutations",
    "Combinations",
    "Advanced Topics"
  ],
  "sections": [
    {
      "id": 0,
      "title": "Permutations",
      "level": 1,
      "content": "...",
      "page_start": 2,
      "page_end": 5,
      "confidence": 0.85,
      "subsections": [
        {
          "id": 0,
          "title": "Basic Permutations",
          "level": 2,
          "content": "..."
        }
      ]
    }
  ],
  "tables": []
}
```

## Configuration

Edit `config.json` to customize extraction parameters:

```json
{
  "extraction": {
    "syllabus": {
      "font_size_threshold": 1.2,
      "position_threshold": 50.0
    },
    "notes": {
      "font_size_threshold": 1.15,
      "position_threshold": 60.0
    }
  }
}
```

### Parameters

- **font_size_threshold**: Ratio for detecting larger fonts as headings (e.g., 1.2 = 20% larger than base)
- **position_threshold**: X-coordinate threshold (in points) for left-aligned content
- **min_heading_confidence**: Minimum confidence score (0-1) for heading detection

## Architecture

### Core Components

1. **PDFExtractor**: Base class providing core PDF reading functionality
2. **StructureDetector**: Analyzes document structure using multiple detection strategies
3. **HierarchyBuilder**: Builds nested JSON structures from detected sections
4. **SyllabusExtractor**: Specialized extractor for syllabus documents
5. **NotesExtractor**: Specialized extractor for lecture notes
6. **LaTeXConverter**: Converts JSON data back to LaTeX format with proper escaping

### Detection Strategies

The system uses multiple strategies to identify document structure:

1. **Font Analysis**: Compares font sizes to identify headings
2. **Position Analysis**: Uses text alignment and spacing
3. **Pattern Recognition**:
   - Numbered sections (1., 1.1, etc.)
   - ALL CAPS text
   - Title Case headings
   - Short lines (potential headings)

## Use Cases for Manim Integration

The hierarchical JSON output enables:

- **Selective Animation**: Access specific sections by index
- **Nested Scenes**: Create parent-child scene relationships matching document structure
- **Metadata Access**: Use page numbers, confidence scores for animation logic
- **Table Visualization**: Extract and animate schedule or grading tables
- **Topic Navigation**: Build interactive animations based on the index

Example Manim integration:

```python
import json
from manim import *

class AnimateSyllabus(Scene):
    def construct(self):
        # Load extracted data
        with open('output/syllabus.json', 'r') as f:
            syllabus = json.load(f)
        
        # Animate index
        title = Text("Course Topics")
        self.play(Write(title))
        
        # Animate each section
        for section in syllabus['sections']:
            section_text = Text(section['title'])
            content_text = Text(section['content'][:100] + "...")
            self.play(Transform(title, section_text))
            self.play(Write(content_text))
```

## Troubleshooting

### No Headings Detected

If the system doesn't detect headings properly:

1. Adjust `font_size_threshold` in `config.json` (lower = more sensitive)
2. Check if your PDF uses consistent formatting
3. The system will fallback to single-section extraction

### Incorrect Section Boundaries

If sections are split incorrectly:

1. Adjust `position_threshold` for alignment detection
2. Check the `confidence` scores in the output JSON
3. Modify detection parameters for your specific PDF format

### Missing Content

If content is missing:

1. Verify the PDF has extractable text (not scanned images)
2. Check for complex layouts that may confuse the extractor
3. Review the `raw_text` output for debugging

## File Structure

```
Manim-MCP/
├── extraction.py           # Main extraction code
├── convert_to_latex.py    # Standalone LaTeX converter
├── requirements.txt        # Python dependencies
├── config.json            # Configuration parameters
├── README.md              # This file
├── testfiles/             # Input PDF files
│   ├── DiscreteMath_Syllabus.pdf
│   └── DiscreteMath_Combinatronics.pdf
└── output/                # Generated files
    ├── syllabus.json      # Structured syllabus data
    ├── syllabus.tex       # LaTeX version of syllabus
    ├── notes.json         # Structured notes data
    └── notes.tex          # LaTeX version of notes
```

## Contributing

To add support for new document types:

1. Create a new extractor class inheriting from `PDFExtractor`
2. Override the `extract()` method
3. Customize detection parameters as needed

Example:

```python
class CustomExtractor(PDFExtractor):
    def extract(self, output_path=None):
        formatted_text = self.extract_text_with_formatting()
        detector = StructureDetector(
            formatted_text,
            font_size_threshold=1.3,  # Custom threshold
            position_threshold=40.0
        )
        # ... rest of extraction logic
```

## License

This project is open source and available for educational purposes.

