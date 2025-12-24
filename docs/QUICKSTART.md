# Quick Start Guide

Get up and running with Manim-MCP in 5 minutes!

## Step 1: Install Dependencies

```bash
cd Manim-MCP
pip install -r requirements.txt
```

## Step 2: Configure OpenAI API

```bash
# Copy example env file
cp config/env.example .env

# Edit .env and add your API key
# OPENAI_API_KEY=sk-your-key-here
```

Get your API key from: https://platform.openai.com/api-keys

## Step 3: Run Your First Generation

### Command Line

```bash
# Generate with AI enhancement
python main.py examples/example_input.json

# Output will be in output/syllabus.md
```

### Without AI (Faster)

```bash
python main.py examples/example_input.json --no-ai
```

### Custom Output Path

```bash
python main.py examples/example_input.json -o my_output.md
```

## Step 4: Use in Python

Create a file `test_generation.py`:

```python
from src.core.syllabus_generator import convert_json_to_syllabus

# Generate syllabus
syllabus = convert_json_to_syllabus(
    'examples/example_input.json',
    output_path='output/test_syllabus.md',
    use_professor=True  # Use AI enhancement
)

print("✅ Generated!")
print(syllabus[:500])  # Print first 500 chars
```

Run it:

```bash
python test_generation.py
```

## Step 5: View Your Output

```bash
# View the generated syllabus
cat output/syllabus.md

# Or open in your favorite editor
code output/syllabus.md
```

## What You'll See

The generated syllabus includes:

1. **Header** - Document metadata
2. **AI Overview** - Generated introduction
3. **Table of Contents** - Section list
4. **Detailed Sections** with:
   - Comprehensive explanations
   - LaTeX equations
   - Animation suggestions
   - Pacing notes
5. **Production Notes** - Next steps

## Next Steps

- [Read the full documentation](USAGE.md)
- [Explore examples](../examples/)
- [Customize configuration](../config/config.yaml)
- [Learn the Python API](API.md)

## Troubleshooting

### Import Errors

Make sure you're in the project root:

```bash
cd /path/to/Manim-MCP
python main.py ...
```

### No API Key

Check your `.env` file exists and has the correct key:

```bash
cat .env
# Should show: OPENAI_API_KEY=sk-...
```

### Can't Find Input File

Use full path or relative to current directory:

```bash
python main.py /full/path/to/input.json
# or
python main.py examples/example_input.json
```

## Tips

1. **Start without AI** to test quickly: `--no-ai`
2. **Check examples** folder for inspiration
3. **Customize config** in `config/config.yaml`
4. **Save API costs** by caching results (saved in output/)

## Command Reference

```bash
# Full command options
python main.py <input.json> [OPTIONS]

Options:
  -o, --output PATH    Output file path (default: output/syllabus.md)
  --no-ai              Disable AI enhancement
  --config PATH        Custom config file
  --api-key KEY        OpenAI API key (or use env var)
```

Happy generating! 🎓

