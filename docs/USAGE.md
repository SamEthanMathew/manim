# JSON to Teaching Syllabus Converter

## Overview
This tool converts structured JSON data (from PDFs, syllabi, or class notes) into a formatted, AI-readable teaching syllabus optimized for Manim scene generation.

## Purpose
The generated syllabus serves as an intermediate format that:
- Structures content hierarchically for easy understanding
- Includes specific animation hints and teaching instructions
- Provides pacing and visual guidance for Manim code generation
- Makes it easier for the Scene Animator to create educational videos

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
                "key1": "value1",
                "key2": ["item1", "item2"],
                "nested": {
                    "subkey": "subvalue"
                }
            }
        }
    ]
}
```

### Fields:
- **document_type**: Type of document (e.g., "syllabus", "lecture_notes", "course_outline")
- **index**: Array of main topics/sections
- **sections**: Array of section objects with:
  - **id**: Unique section identifier (integer)
  - **title**: Section title
  - **content**: Can be a dict, list, or string with the section's content

## Usage

### Basic Usage (Python)

```python
from json_to_syllabus import convert_json_to_syllabus

# From JSON file
syllabus = convert_json_to_syllabus('input.json', 'output_syllabus.md')

# From JSON string
import json
data = {"document_type": "syllabus", ...}
syllabus = convert_json_to_syllabus(json.dumps(data))
print(syllabus)
```

### Command Line Usage

```bash
# Run the example
python json_to_syllabus.py

# Convert a specific JSON file
python -c "from json_to_syllabus import convert_json_to_syllabus; convert_json_to_syllabus('your_input.json', 'your_output.md')"
```

### Using the SyllabusGenerator Class

```python
from json_to_syllabus import SyllabusGenerator
import json

# Load your JSON data
with open('input.json', 'r') as f:
    data = json.load(f)

# Create generator
generator = SyllabusGenerator(data)

# Generate syllabus
syllabus_text = generator.generate_syllabus()

# Save to file
generator.save_to_file('output.md')
```

## Output Format

The generated syllabus includes:

1. **Header**: Document type, purpose, and metadata
2. **Table of Contents**: List of all topics with animation notes
3. **Detailed Sections**: For each section:
   - Section number and title
   - Formatted content (structured based on input)
   - **Teaching Instructions for Manim**:
     - Key topic identification
     - Suggested visual elements
     - Animation style recommendations
     - Pacing guidelines
     - Transition suggestions

## Example

See `example_input.json` and `example_output.md` for a complete example.

### Input (`example_input.json`):
```json
{
    "document_type": "syllabus",
    "index": ["Course Information", "Topics Covered"],
    "sections": [
        {
            "id": 0,
            "title": "Course Information",
            "content": {
                "course_name": "Intro to Python",
                "instructor": "Dr. Smith"
            }
        }
    ]
}
```

### Output:
```markdown
# TEACHING SYLLABUS
## Document Type: SYLLABUS

## TABLE OF CONTENTS
1. Course Information
2. Topics Covered

### Section 1: Course Information
---
**Course Name**: Intro to Python
**Instructor**: Dr. Smith

**Teaching Instructions for Manim**:
- **Key Topic**: Course Information
- **Suggested Visuals**:
  - Create visual cards for each key point
  ...
```

## Integration with Pipeline

This tool fits into your pipeline as follows:

```
PDF → pdfplumber → AI Processing → JSON → [THIS TOOL] → Teaching Syllabus → Scene Animator → Manim Code
```

1. **Input**: Receives structured JSON from PDF processing
2. **Processing**: Converts to teaching-focused syllabus format
3. **Output**: Provides AI-readable syllabus with animation instructions
4. **Next Step**: Feed output to Scene Animator for Manim code generation

## Customization

You can customize the `SyllabusGenerator` class to:
- Add more specific animation instructions
- Change the output format
- Add subject-specific teaching guidelines
- Include more detailed visual suggestions
- Adjust pacing recommendations

## Files

- `json_to_syllabus.py`: Main converter script
- `example_input.json`: Example JSON input
- `example_output.md`: Example generated syllabus
- `USAGE.md`: This file

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

