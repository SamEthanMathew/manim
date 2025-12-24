# Setup Guide

## Environment Setup

This project uses miniconda for Python environment management.

### Option 1: Using Conda Base Environment (Recommended)

The project is currently configured to use the miniconda base environment with a custom Jupyter kernel.

**Jupyter Kernel**: `Manim-MCP (Python 3.13)`

#### Installation Complete ✅

The following packages are already installed:
- ipykernel
- jupyter
- All dependencies from requirements.txt

#### To Use the Notebooks:

1. Open any `.ipynb` file in Cursor or Jupyter
2. Select the kernel: **"Manim-MCP (Python 3.13)"**
3. Run the cells!

### Option 2: Creating a New Conda Environment (Alternative)

If you want a separate environment:

```bash
# Create new environment
conda create -n manim-mcp python=3.11 -y

# Activate it
conda activate manim-mcp

# Install dependencies
pip install -r requirements.txt

# Register kernel
python -m ipykernel install --user --name manim-mcp --display-name "Manim-MCP (Python 3.11)"
```

### Option 3: Using venv (Not Recommended for this project)

If you prefer venv:

```bash
# Create venv
python -m venv .venv

# Activate
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Register kernel
python -m ipykernel install --user --name manim-mcp-venv
```

## Verify Installation

Test that everything works:

```bash
# Check available kernels
jupyter kernelspec list

# Test imports
python -c "import ipykernel; from json_to_syllabus import convert_json_to_syllabus; print('✅ All good!')"
```

## Running the Demo

```bash
# Start Jupyter
jupyter notebook demo.ipynb

# Or use Jupyter Lab
jupyter lab demo.ipynb
```

In Cursor, just open `demo.ipynb` and select the **"Manim-MCP (Python 3.13)"** kernel.

## Dependencies

See `requirements.txt` for the full list. The main converter (`json_to_syllabus.py`) has **zero external dependencies** and uses only Python standard library.

Additional packages for notebooks:
- ipykernel - Jupyter kernel support
- jupyter - Jupyter notebook environment

Future additions:
- manim - Animation library (when you build the Scene Animator)
- pydub - Audio processing (for adding narration)

## Troubleshooting

### "No module named 'ipykernel'"
- Make sure you selected the correct kernel in Jupyter
- Run: `pip install ipykernel jupyter`

### "Kernel died" or kernel issues
- Restart the kernel: Kernel → Restart
- Check Python version: `python --version`
- Reinstall kernel: `python -m ipykernel install --user --name manim-mcp --display-name "Manim-MCP (Python 3.13)"`

### Permission errors with conda
- Use conda base environment (already active)
- Or use `--user` flag with pip: `pip install --user package_name`

## Current Status

✅ Conda environment configured  
✅ Jupyter kernel installed: `Manim-MCP (Python 3.13)`  
✅ Dependencies installed  
✅ Notebooks ready to run  

You're all set! 🚀

