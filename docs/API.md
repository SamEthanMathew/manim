# API Reference

Complete Python API documentation for Manim-MCP.

## Core Module

### `convert_json_to_syllabus`

Main conversion function.

```python
from src.core.syllabus_generator import convert_json_to_syllabus

syllabus = convert_json_to_syllabus(
    json_input: str,
    output_path: str = None,
    use_professor: bool = True,
    config_path: str = None,
    api_key: str = None
) -> str
```

**Parameters:**
- `json_input`: JSON string or path to JSON file
- `output_path`: Where to save output (optional)
- `use_professor`: Enable AI enhancement (default: True)
- `config_path`: Custom config file path (optional)
- `api_key`: OpenAI API key (optional, uses env var)

**Returns:** Generated syllabus as string

**Example:**

```python
syllabus = convert_json_to_syllabus(
    'input.json',
    output_path='output/syllabus.md',
    use_professor=True
)
```

### `SyllabusGenerator`

Main generator class for custom workflows.

```python
from src.core.syllabus_generator import SyllabusGenerator

generator = SyllabusGenerator(
    json_data: Dict[str, Any],
    use_professor: bool = True,
    config: Dict[str, Any] = None,
    api_key: str = None
)
```

**Methods:**

#### `generate_syllabus() -> str`

Generate complete syllabus.

```python
syllabus = generator.generate_syllabus()
```

#### `save_to_file(output_path: str) -> None`

Save syllabus to file.

```python
generator.save_to_file('output/my_syllabus.md')
```

**Example:**

```python
import json

with open('input.json') as f:
    data = json.load(f)

generator = SyllabusGenerator(data, use_professor=True)
syllabus = generator.generate_syllabus()
generator.save_to_file('output.md')
```

## Professor Module

### `ProfessorAgent`

AI Professor for content enhancement.

```python
from src.professor.professor_agent import ProfessorAgent

professor = ProfessorAgent(
    config: Dict[str, Any] = None,
    api_key: str = None
)
```

**Methods:**

#### `enhance_section(title, content, context="") -> Dict[str, str]`

Enhance a single section with AI.

```python
enhanced = professor.enhance_section(
    title="Machine Learning Basics",
    content={"topic": "Supervised Learning"},
    context="Introductory course"
)
```

**Returns:**
```python
{
    "full_content": "...",        # Complete enhanced content
    "explanation": "...",          # Main explanation
    "key_concepts": "...",         # Key concepts section
    "equations": [...],            # List of LaTeX equations
    "animation_ideas": "...",      # Animation suggestions
    "pacing_notes": "..."          # Pacing recommendations
}
```

#### `generate_syllabus_overview(document_type, sections) -> str`

Generate course overview.

```python
overview = professor.generate_syllabus_overview(
    document_type="syllabus",
    sections=[{"title": "Intro"}, {"title": "Concepts"}]
)
```

#### `suggest_visual_style(topic, content_type="educational") -> Dict`

Get visual style suggestions.

```python
style = professor.suggest_visual_style(
    topic="Linear Algebra",
    content_type="technical"
)
# Returns: {
#     "color_palette": ["#3498db", ...],
#     "style": "modern",
#     "description": "..."
# }
```

**Example:**

```python
from src.professor.professor_agent import ProfessorAgent
import os

professor = ProfessorAgent(api_key=os.getenv('OPENAI_API_KEY'))

# Enhance content
enhanced = professor.enhance_section(
    title="Calculus Fundamentals",
    content={
        "topics": ["Derivatives", "Integrals"],
        "level": "undergraduate"
    }
)

print(enhanced['full_content'])
```

## Utilities

### Config Loader

```python
from src.utils.config_loader import load_config, get_api_key

# Load configuration
config = load_config('config/config.yaml')

# Get API key from environment
api_key = get_api_key()
```

### LaTeX Formatter

```python
from src.utils.latex_formatter import (
    format_latex,
    escape_latex,
    extract_equations,
    format_equation_for_manim
)

# Format LaTeX text
formatted = format_latex("Einstein said $E=mc^2$")

# Escape special LaTeX characters
safe_text = escape_latex("Cost is $100 & tax is 20%")

# Extract equations from text
equations = extract_equations("Inline $x^2$ and block $$y=mx+b$$")
# Returns: [("x^2", "inline"), ("y=mx+b", "block")]

# Format for Manim
manim_eq = format_equation_for_manim("$$E = mc^2$$")
# Returns: "E = mc^2" (without delimiters)
```

## Complete Example

Full workflow using the API:

```python
import json
import os
from pathlib import Path

from src.core.syllabus_generator import SyllabusGenerator
from src.professor.professor_agent import ProfessorAgent
from src.utils.config_loader import load_config

# 1. Load configuration
config = load_config()

# 2. Load input JSON
with open('examples/example_input.json') as f:
    data = json.load(f)

# 3. Create professor (optional, for direct access)
professor = ProfessorAgent(
    config=config,
    api_key=os.getenv('OPENAI_API_KEY')
)

# Get visual style suggestions
style = professor.suggest_visual_style(data['sections'][0]['title'])
print(f"Suggested colors: {style.get('color_palette', [])}")

# 4. Generate syllabus
generator = SyllabusGenerator(
    data,
    use_professor=True,
    config=config
)

syllabus = generator.generate_syllabus()

# 5. Save output
output_dir = Path('output')
output_dir.mkdir(exist_ok=True)

generator.save_to_file('output/my_syllabus.md')

print("✅ Complete!")
print(f"Generated {len(syllabus)} characters")
```

## Error Handling

All functions handle errors gracefully:

```python
try:
    syllabus = convert_json_to_syllabus('input.json')
except FileNotFoundError as e:
    print(f"Input file not found: {e}")
except ValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

The system will fall back to basic generation if AI enhancement fails.

## Configuration

Default config structure:

```yaml
openai:
  api_key: ${OPENAI_API_KEY}
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 4000

professor:
  system_prompt: "..."
  use_web_search: true
  enhance_with_research: true

syllabus:
  output_format: "markdown"
  include_latex: true
  include_animation_hints: true
```

Access in code:

```python
from src.utils.config_loader import load_config

config = load_config()
model = config['openai']['model']
temp = config['openai']['temperature']
```

## Type Hints

All functions include type hints for better IDE support:

```python
from typing import Dict, List, Any, Optional

def convert_json_to_syllabus(
    json_input: str,
    output_path: Optional[str] = None,
    use_professor: bool = True,
    config_path: Optional[str] = None,
    api_key: Optional[str] = None
) -> str:
    ...
```

## Next Steps

- See [Usage Guide](USAGE.md) for practical examples
- Check [Quick Start](QUICKSTART.md) for getting started
- Read [main README](../README.md) for overview

