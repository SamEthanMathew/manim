# System Architecture

## Pipeline Overview

Manim-MCP converts educational documents into rich, animated videos through a multi-stage pipeline:

```mermaid
graph LR
    A[PDF Document] --> B[TextExtractor]
    B --> C[Structured JSON]
    C --> D[Syllabus Generator]
    D -- "With AI Professor" --> E[Teaching Syllabus]
    E --> F[Scene Animator]
    F --> G[Manim Video]
```

## Component Breakdown

### 1. TextExtractor (`src/text_extractor/`)
**Purpose**: Extracts structured text from raw PDFs.
- Uses `pdfplumber` to analyze layout and fonts.
- Detects hierarchy (headings, sections) automatically.
- Outputs standardized JSON.

### 2. Syllabus Generator (`src/core/`)
**Purpose**: Converts raw JSON into a teaching guide.
- **Input**: JSON (from TextExtractor or manual).
- **Output**: Markdown with LaTeX equations and animation hints.
- **Professor Agent**: Connects to OpenAI GPT-4 to enhance content with explanations, visual metaphors, and pacing.

### 3. Pipeline Integration (`src/pipeline.py`)
**Purpose**: Connects the extractor and generator.
- Handles format detection (PDF vs JSON).
- Manages the flow of data between components.
- Error handling and logging.

## Project Structure

```
Manim-MCP/
├── src/
│   ├── text_extractor/          # PDF extraction logic
│   ├── core/                    # Syllabus generation logic
│   ├── professor/               # AI Agent (GPT-4 integration)
│   ├── utils/                   # Shared utilities (Config, LaTeX)
│   └── pipeline.py              # Main integration glue
│
├── config/                      # Configuration files
├── docs/                        # Documentation
├── examples/                    # Sample inputs/outputs
├── output/                      # Generated artifacts
│
├── main.py                      # CLI Entry Point
└── requirements.txt             # Dependencies
```

