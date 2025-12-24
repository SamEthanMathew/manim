# Manim-MCP

**AI-Powered Educational Video Pipeline**

Manim-MCP converts static educational documents (PDFs, Syllabi) into rich, animated video scripts. It uses AI to act as a "Professor," explaining concepts, generating LaTeX equations, and designing Manim animations for every topic.

## 🚀 Quick Start

1. **Install**: `pip install -r requirements.txt`
2. **Setup**: Add your `OPENAI_API_KEY` to `.env`
3. **Run**: 
   ```bash
   python main.py my_course_syllabus.pdf
   ```

## 📚 Documentation

- **[Installation Guide](docs/setup.md)**: Detailed setup instructions.
- **[Usage Guide](docs/usage.md)**: CLI and Python API examples.
- **[System Architecture](docs/architecture.md)**: How the pipeline works.
- **[API Reference](docs/API.md)**: Source code documentation.

## ⚡ Features
- **PDF Extraction**: Intelligently parses layout and hierarchy.
- **AI Professor**: GPT-4 enhances content with explanations and visual metaphors.
- **LaTeX Support**: Automatically formats math equations.
- **Animation-Ready**: Outputs structured guides ready for Manim code generation.

## 📂 Examples
Check the `examples/` folder or run `python demo.py` to see the system in action.
