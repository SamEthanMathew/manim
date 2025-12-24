# Manim-MCP: PDF to Manim Video Pipeline

An AI-powered pipeline that converts PDFs, syllabi, and class notes into educational videos using Manim, complete with animations and audio.

## Overview

This project is part of a larger pipeline that:
1. **PDF Processing** (Your friend's work): Extracts content from PDFs using `pdfplumber` and converts to structured JSON
2. **Syllabus Generation** (This component): Converts JSON into AI-readable teaching syllabus
3. **Scene Animation** (Next step): Generates Manim Python code from the syllabus
4. **Video Rendering**: Renders Manim animations and adds audio

## Current Component: JSON to Teaching Syllabus

This component transforms structured JSON data into a formatted, AI-readable teaching syllabus optimized for Manim scene generation.

### Features

- ✅ **Flexible Input**: Accepts JSON from files or strings
- ✅ **Structured Output**: Generates markdown-formatted syllabus with clear hierarchy
- ✅ **Animation Hints**: Includes specific instructions for Manim animations
- ✅ **Teaching Guidance**: Provides pacing, visual suggestions, and transition recommendations
- ✅ **Content Parsing**: Handles nested dictionaries, lists, and various content structures
- ✅ **Easy Integration**: Simple API for pipeline integration

## Quick Start

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd Manim-MCP

# No external dependencies needed - uses Python standard library only!
```

### Basic Usage

```python
from json_to_syllabus import convert_json_to_syllabus

# From a JSON file
syllabus = convert_json_to_syllabus('input.json', 'output.md')

# From JSON string
import json
data = {
    "document_type": "syllabus",
    "index": ["Topic 1", "Topic 2"],
    "sections": [...]
}
syllabus = convert_json_to_syllabus(json.dumps(data))
print(syllabus)
```

### Interactive Demo

Check out `demo.ipynb` for an interactive Jupyter notebook demonstration!

## Project Structure

```
Manim-MCP/
├── json_to_syllabus.py      # Main converter script
├── example_input.json        # Example JSON input
├── example_output.md         # Example generated syllabus
├── demo.ipynb               # Interactive demo notebook
├── USAGE.md                 # Detailed usage guide
├── README.md                # This file
└── requirements.txt         # Python dependencies (if any)
```

## Input Format

Your JSON should follow this structure:

```json
{
    "document_type": "syllabus",
    "index": ["Topic 1", "Topic 2", "Topic 3"],
    "sections": [
        {
            "id": 0,
            "title": "Section Title",
            "content": {
                "key": "value",
                "nested": ["item1", "item2"]
            }
        }
    ]
}
```

## Output Format

The generated syllabus includes:

1. **Header**: Document metadata and purpose
2. **Table of Contents**: List of topics with animation notes
3. **Detailed Sections**: For each section:
   - Formatted content
   - Teaching Instructions for Manim:
     - Key topic identification
     - Suggested visual elements
     - Animation style recommendations
     - Pacing guidelines (3-5 seconds per point)
     - Transition suggestions

Example output:

```markdown
# TEACHING SYLLABUS
## Document Type: SYLLABUS

## TABLE OF CONTENTS
1. Introduction
2. Key Concepts

### Section 1: Introduction
---
**Topic**: Machine Learning Basics
**Duration**: 5 minutes

**Teaching Instructions for Manim**:
- **Key Topic**: Introduction
- **Suggested Visuals**:
  - Create visual cards for each key point
  - Use hierarchical text animations
- **Animation Style**: Text fade-in, emphasize key terms
- **Pacing**: Allow 3-5 seconds per major point
```

## Pipeline Integration

```
┌─────────┐      ┌───────────┐      ┌──────────────┐      ┌──────────┐
│   PDF   │─────▶│ pdfplumber│─────▶│     AI       │─────▶│   JSON   │
└─────────┘      └───────────┘      │  Processing  │      └─────┬────┘
                                     └──────────────┘            │
                                                                 │
                                                                 ▼
┌─────────┐      ┌───────────┐      ┌──────────────┐      ┌──────────┐
│  Video  │◀─────│   Audio   │◀─────│    Manim     │◀─────│ Teaching │
│ Output  │      │   Added   │      │   Renderer   │      │ Syllabus │
└─────────┘      └───────────┘      └──────────────┘      └──────────┘
                                            ▲                    │
                                            │                    │
                                            │     ┌──────────────┘
                                            │     │
                                     ┌──────┴─────▼────┐
                                     │ Scene Animator  │ ◀── YOU ARE HERE
                                     │ (Manim Code)    │
                                     └─────────────────┘
```

## Examples

See the following files for complete examples:
- `example_input.json` - Sample input JSON
- `example_output.md` - Corresponding generated syllabus
- `demo.ipynb` - Interactive examples

## Documentation

- **USAGE.md** - Comprehensive usage guide with examples
- **demo.ipynb** - Interactive Jupyter notebook demonstrations
- **Docstrings** - All functions and classes are documented

## Customization

The `SyllabusGenerator` class can be extended to:
- Add subject-specific teaching instructions
- Customize animation style recommendations
- Adjust pacing and transition suggestions
- Modify output format
- Add more detailed visual guidance

## Requirements

- Python 3.7+
- No external dependencies (standard library only)

## Next Steps

1. **For this component**: Feed your processed JSON into `json_to_syllabus.py`
2. **Next component**: Use the generated syllabus to create Manim scene code
3. **Final steps**: Render animations and add audio narration

## Contributing

This is part of a larger educational video generation pipeline. Feel free to:
- Extend the teaching instructions for specific subjects
- Add more animation style templates
- Improve content parsing for complex structures
- Integrate with the Scene Animator component

## License

[Add your license here]

## Authors

- Pipeline Design: You and your friend
- Syllabus Generator: This component
- PDF Processing: Your friend's component
- Scene Animator: Coming next!

---

**Status**: ✅ Syllabus Generator Complete | 🚧 Scene Animator In Progress

