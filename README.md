# Manim-MCP: AI-Powered Educational Video Pipeline

Transform PDFs, syllabi, and class notes into engaging educational videos with AI-generated content, LaTeX equations, and Manim animations.

## 🎯 Overview

Manim-MCP is an intelligent pipeline that converts educational documents into rich, animated videos:

```
PDF → pdfplumber → AI Processing → JSON → [Syllabus Generator] → Teaching Guide → Scene Animator → Manim → Video + Audio
                                              ↑ YOU ARE HERE
```

### Key Features

- ✨ **AI Professor Integration**: Uses OpenAI GPT-4 to generate comprehensive teaching content
- 📐 **LaTeX Support**: Automatic equation generation and formatting
- 🎨 **Animation Suggestions**: Specific Manim animation recommendations for each concept
- 📚 **Structured Output**: Markdown/LaTeX format optimized for video production
- 🔄 **Flexible**: Works with or without AI enhancement
- 🎓 **Educational Focus**: Designed specifically for teaching and learning

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <your-repo>
cd Manim-MCP

# Install dependencies
pip install -r requirements.txt

# Set up your OpenAI API key
cp config/env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Basic Usage

```bash
# Generate AI-enhanced syllabus
python main.py examples/example_input.json -o output/my_syllabus.md

# Without AI (faster, basic)
python main.py examples/example_input.json --no-ai -o output/basic.md
```

### Python API

```python
from src.core.syllabus_generator import convert_json_to_syllabus

# With AI enhancement
syllabus = convert_json_to_syllabus(
    'input.json',
    output_path='output/syllabus.md',
    use_professor=True
)

# Without AI
syllabus = convert_json_to_syllabus(
    'input.json',
    use_professor=False
)
```

## 📁 Project Structure

```
Manim-MCP/
├── src/
│   ├── core/                   # Core syllabus generation
│   │   └── syllabus_generator.py
│   ├── professor/              # AI Professor agent
│   │   └── professor_agent.py
│   └── utils/                  # Utilities
│       ├── config_loader.py
│       └── latex_formatter.py
├── config/
│   ├── config.yaml            # Main configuration
│   └── env.example            # Environment variables template
├── examples/                   # Example inputs and outputs
├── output/                     # Generated syllabi (gitignored)
├── docs/                       # Documentation
├── tests/                      # Tests (future)
├── main.py                     # CLI entry point
└── requirements.txt            # Python dependencies
```

## 🎓 How It Works

### 1. Input JSON Format

```json
{
    "document_type": "syllabus",
    "index": ["Introduction", "Key Concepts", "Applications"],
    "sections": [
        {
            "id": 0,
            "title": "Introduction",
            "content": {
                "topic": "Machine Learning Basics",
                "objectives": ["Understand ML", "Learn terminology"]
            }
        }
    ]
}
```

### 2. AI Enhancement

The **Professor Agent**:
- Analyzes each section
- Generates detailed explanations
- Creates relevant LaTeX equations
- Suggests specific Manim animations
- Provides pacing and visual style guidance

### 3. Output Format

Generated syllabi include:

```markdown
# TEACHING SYLLABUS

## Overview
[AI-generated introduction and learning objectives]

## Detailed Sections

### Section 1: Machine Learning Basics

**Explanation**: [Comprehensive AI-generated content]

**Key Concepts**:
- Supervised Learning: $y = f(x)$
- Loss Function: $$L = \frac{1}{n}\sum_{i=1}^n (y_i - \hat{y}_i)^2$$

**Animation Suggestions**:
- Open with title fade-in
- Visualize data points appearing one by one
- Animate the function fitting process
- Highlight equation terms with color
- Show loss decreasing over iterations

**Pacing**: 5-7 seconds per concept
```

## 🛠️ Configuration

Edit `config/config.yaml`:

```yaml
openai:
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 4000

professor:
  use_web_search: true
  enhance_with_research: true
```

## 📚 Documentation

- [Setup Guide](docs/SETUP.md) - Installation and environment setup
- [Usage Guide](docs/USAGE.md) - Detailed usage instructions
- [API Reference](docs/API.md) - Python API documentation
- [Examples](examples/) - Sample inputs and outputs

## 🎨 Features in Detail

### AI Professor Agent

The Professor Agent (GPT-4) provides:
- **Context-Aware Content**: Understands the subject and generates appropriate explanations
- **Mathematical Rigor**: Creates accurate LaTeX equations
- **Visual Thinking**: Suggests animations based on pedagogical best practices
- **Adaptive Style**: Adjusts tone and complexity based on content

### LaTeX Integration

- Inline math: `$E = mc^2$`
- Display equations: `$$\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$$`
- Automatic conversion to Manim format
- Equation extraction and validation

### Animation Guidance

Specific suggestions for Manim:
- Scene composition
- Object introductions
- Transformations and morphs
- Color schemes
- Timing and pacing
- Transitions between concepts

## 🔧 Advanced Usage

### Custom Configuration

```python
from src.core.syllabus_generator import SyllabusGenerator
from src.utils.config_loader import load_config

config = load_config('path/to/custom_config.yaml')
generator = SyllabusGenerator(data, config=config, use_professor=True)
syllabus = generator.generate_syllabus()
```

### Programmatic Control

```python
from src.professor.professor_agent import ProfessorAgent

# Initialize professor
professor = ProfessorAgent(api_key='your-key')

# Enhance a single section
enhanced = professor.enhance_section(
    title="Quantum Mechanics",
    content={"topic": "Wave functions", "level": "undergraduate"},
    context="Introductory physics course"
)

# Get visual style suggestions
style = professor.suggest_visual_style("Linear Algebra", "technical")
```

## 🤝 Integration with Pipeline

### Input (From Friend's Component)

Your friend's PDF processor outputs JSON → This component

### Output (To Scene Animator)

This component outputs structured syllabus → Scene Animator generates Manim code

## 📦 Dependencies

- **openai**: GPT-4 integration
- **pyyaml**: Configuration management
- **python-dotenv**: Environment variables
- **Standard Library**: JSON, pathlib, re, etc.

## 🚧 Roadmap

- [x] Basic syllabus generation
- [x] AI Professor integration
- [x] LaTeX support
- [x] Animation suggestions
- [ ] Web search integration for research
- [ ] Scene Animator component
- [ ] Audio narration generation
- [ ] Full Manim code generation
- [ ] End-to-end video pipeline

## 🔒 Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional
OPENAI_MODEL=gpt-4o
OUTPUT_DIR=output
```

## 💡 Examples

Check the `examples/` directory:
- `example_input.json` - Sample input
- `example_output.md` - AI-generated output
- `demo.ipynb` - Interactive Jupyter demo

## 🐛 Troubleshooting

### "OpenAI API key not found"
Set `OPENAI_API_KEY` in `.env` file or environment

### "Professor AI not available"
System will fall back to basic generation without AI

### "Import errors"
Make sure you're running from project root or update `PYTHONPATH`

## 📄 License

[Add your license]

## 👥 Contributors

- Pipeline architecture: Your team
- Syllabus Generator: This component
- PDF Processing: Your friend's component

---

**Status**: ✅ Syllabus Generator v0.1.0 Complete  
**Next**: Scene Animator (Manim code generation)

