# Usage Guide

## CLI Reference

The main entry point is `main.py`. It automatically detects whether you are providing a PDF or a JSON file.

### Basic Syntax
```bash
python main.py <input_file> [options]
```

### Common Commands

**Process a PDF (Complete Pipeline)**
```bash
python main.py documents/calculus.pdf -o output/syllabus.md
```

**Process a specific document type**
If processing lecture notes instead of a syllabus:
```bash
python main.py notes.pdf --type notes
```

**Run without AI (Offline/Fast Mode)**
Skips the GPT-4 enhancement step. Useful for debugging extraction.
```bash
python main.py document.pdf --no-ai
```

**Process raw JSON**
If you already have structured JSON:
```bash
python main.py examples/example_input.json
```

## Python API

You can use the pipeline components directly in your own scripts.

### Complete Pipeline
```python
from src.pipeline import pdf_to_syllabus

syllabus = pdf_to_syllabus(
    pdf_path="lecture.pdf",
    output_path="output/guide.md",
    use_ai=True
)
```

### Component: Professor Agent
```python
from src.professor.professor_agent import ProfessorAgent

prof = ProfessorAgent()
content = prof.enhance_section(
    title="Derivatives",
    content="Rate of change...",
    context="Calculus I"
)
print(content['animation_ideas'])
```

## Configuration

Configuration is handled in `config/config.yaml`.

```yaml
openai:
  model: "gpt-4o"
  temperature: 0.7

syllabus:
  output_format: "markdown"
  include_latex: true
```

<!-- End of Guide -->
