# 🎓 Getting Started with Manim-MCP

Welcome to Manim-MCP! This is your AI-powered pipeline for turning PDFs and educational content into animated videos.

## 🚀 Quick Start (2 Minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Try Without AI (No Setup Needed)
```bash
python main.py examples/example_input.json --no-ai
# Output: output/syllabus.md
```

### 3. View Your Output
```bash
cat output/syllabus.md
```

**That's it!** You now have a teaching syllabus with animation suggestions.

## 🤖 Enable AI Enhancement (Optional)

To get AI-generated explanations and LaTeX equations:

### 1. Get OpenAI API Key
- Visit: https://platform.openai.com/api-keys
- Create a new API key

### 2. Set Environment Variable
```bash
# Copy example
cp config/env.example .env

# Edit .env and add your key
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### 3. Generate with AI
```bash
python main.py examples/example_input.json
# Now includes AI-generated content!
```

## 📁 Project Structure

```
Manim-MCP/
├── src/                    # Source code
│   ├── core/              # Syllabus generation
│   ├── professor/         # AI Professor (GPT-4)
│   └── utils/             # Utilities
├── config/                # Configuration
├── examples/              # Sample files
├── output/                # Your generated files
├── docs/                  # Documentation
├── main.py               # Main CLI tool
└── demo.py               # Run demos
```

## 🎯 Common Tasks

### Generate Syllabus
```bash
# With AI
python main.py input.json -o output/my_syllabus.md

# Without AI (faster)
python main.py input.json --no-ai

# Custom config
python main.py input.json --config my_config.yaml
```

### Run Demos
```bash
python demo.py
# Generates 4 different example syllabi
```

### Use in Python
```python
from src.core.syllabus_generator import convert_json_to_syllabus

syllabus = convert_json_to_syllabus(
    'input.json',
    use_professor=True
)
print(syllabus)
```

## 📝 Input Format

Your JSON should look like this:

```json
{
    "document_type": "syllabus",
    "index": ["Topic 1", "Topic 2"],
    "sections": [
        {
            "id": 0,
            "title": "Topic 1",
            "content": {
                "description": "...",
                "key_points": ["point 1", "point 2"]
            }
        }
    ]
}
```

See `examples/example_input.json` for a complete example.

## 📚 Documentation

- **[README.md](README.md)** - Full project overview
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Detailed quick start
- **[docs/API.md](docs/API.md)** - Python API reference
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - What was built and why

## ⚡ Tips

1. **Start Simple**: Use `--no-ai` first to test quickly
2. **Check Examples**: Look in `examples/` for inspiration
3. **Run Demos**: `python demo.py` shows 4 different use cases
4. **Read Output**: Generated files include animation suggestions
5. **Customize**: Edit `config/config.yaml` for AI behavior

## 🎨 What You Get

The generated syllabus includes:

1. **Header & Metadata** - Document info
2. **Overview** - AI-generated introduction (if enabled)
3. **Table of Contents** - All sections
4. **Detailed Sections** with:
   - Explanations
   - LaTeX equations (e.g., `$E = mc^2$`)
   - Animation suggestions
   - Pacing notes
5. **Production Notes** - Next steps for video creation

## 🔧 Customization

Edit `config/config.yaml` to change:
- AI model (GPT-4, GPT-4-turbo, etc.)
- Temperature (creativity level)
- Output format preferences
- Professor behavior

## 🐛 Troubleshooting

### "Module not found"
```bash
# Make sure you're in the project root
cd /path/to/Manim-MCP
python main.py ...
```

### "OpenAI API key not found"
```bash
# Check your .env file
cat .env
# Should show: OPENAI_API_KEY=sk-...

# Or set directly
export OPENAI_API_KEY="sk-your-key"
```

### "File not found"
```bash
# Use correct path
python main.py examples/example_input.json

# Or full path
python main.py /full/path/to/input.json
```

## 🎓 Next Steps

1. **Try It**: Run `python demo.py`
2. **Generate Your Content**: Use your own JSON
3. **Customize**: Adjust `config/config.yaml`
4. **Integrate**: Connect with Scene Animator (next component)
5. **Create Videos**: Use output to generate Manim code

## 💡 Examples

### Example 1: Basic Course Syllabus
```bash
python main.py examples/example_input.json --no-ai
```

### Example 2: AI-Enhanced Math Lesson
```bash
# Your input.json with calculus content
python main.py my_calculus.json -o output/calculus_syllabus.md
```

### Example 3: Batch Processing
```python
import glob
from src.core.syllabus_generator import convert_json_to_syllabus

for json_file in glob.glob('inputs/*.json'):
    output = f"output/{Path(json_file).stem}_syllabus.md"
    convert_json_to_syllabus(json_file, output_path=output)
```

## 🔄 Pipeline Context

You are here:
```
PDF → JSON → [SYLLABUS GENERATOR] → Teaching Guide → Scene Animator → Video
                    ↑ YOU ARE HERE
```

Your friend provides the JSON, you generate the syllabus, and the Scene Animator (next component) will turn it into Manim code.

## 📞 Need Help?

1. Read [docs/QUICKSTART.md](docs/QUICKSTART.md)
2. Check [docs/API.md](docs/API.md)
3. Run `python demo.py` for examples
4. Look at generated files in `output/`

## ✨ Features

- ✅ AI-powered content generation
- ✅ LaTeX equation support
- ✅ Specific animation suggestions
- ✅ Works offline (without AI)
- ✅ Customizable configuration
- ✅ Well-documented API
- ✅ Production-ready

## 🎉 You're Ready!

Start with:
```bash
python demo.py
```

Then try your own content:
```bash
python main.py your_input.json
```

**Happy teaching!** 🎓

