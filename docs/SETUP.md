# Installation & Setup

## Prerequisites
- Python 3.10+
- OpenAI API Key (for AI features)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-repo/Manim-MCP.git
   cd Manim-MCP
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   Create a `.env` file in the root directory:
   ```bash
   cp config/env.example .env
   ```
   
   Edit `.env` and add your OpenAI key:
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ```

## Verification
Run the demo script to verify everything is working:

```bash
python demo.py
```
If you see "Professor AI initialized", you are ready to go.

<!-- End of Setup Guide -->
