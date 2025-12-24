"""
Enhanced Syllabus Generator with AI Professor Integration
Converts JSON to rich teaching syllabi with LaTeX equations and animation guidance
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from professor.professor_agent import ProfessorAgent
from utils.latex_formatter import format_equation_for_manim, extract_equations
from utils.config_loader import load_config


class SyllabusGenerator:
    """Generates teaching syllabi with AI-enhanced content"""
    
    def __init__(
        self,
        json_data: Dict[str, Any],
        use_professor: bool = True,
        config: Dict[str, Any] = None,
        api_key: str = None
    ):
        """
        Initialize syllabus generator
        
        Args:
            json_data: Input JSON data with sections
            use_professor: Whether to use AI professor for enhancement
            config: Configuration dictionary
            api_key: OpenAI API key (if using professor)
        """
        self.data = json_data
        self.document_type = json_data.get("document_type", "unknown")
        self.index = json_data.get("index", [])
        self.sections = json_data.get("sections", [])
        self.use_professor = use_professor
        self.config = config or {}
        
        # Initialize professor if enabled
        self.professor = None
        if use_professor:
            try:
                self.professor = ProfessorAgent(config=config, api_key=api_key)
                print("✅ Professor AI initialized")
            except Exception as e:
                print(f"⚠️  Professor AI not available: {e}")
                print("   Continuing with basic generation...")
                self.use_professor = False
    
    def generate_syllabus(self) -> str:
        """
        Generate complete teaching syllabus
        
        Returns:
            Markdown/LaTeX formatted syllabus
        """
        syllabus_parts = []
        
        # Header
        syllabus_parts.append(self._generate_header())
        
        # AI-generated overview (if professor available)
        if self.professor:
            syllabus_parts.append(self._generate_ai_overview())
        
        # Table of Contents
        syllabus_parts.append(self._generate_toc())
        
        # Detailed Sections
        syllabus_parts.append(self._generate_sections())
        
        # Footer with metadata
        syllabus_parts.append(self._generate_footer())
        
        return "\n\n".join(syllabus_parts)
    
    def _generate_header(self) -> str:
        """Generate syllabus header"""
        header = f"""# TEACHING SYLLABUS
## {self.document_type.replace('_', ' ').title()}

---
**Purpose**: This syllabus provides structured content for creating educational video animations using Manim.  
**Total Sections**: {len(self.sections)}  
**Format**: Markdown with LaTeX equations  
**Target**: Educational video production with animations  
---"""
        return header
    
    def _generate_ai_overview(self) -> str:
        """Generate AI-powered overview of the course"""
        try:
            overview = self.professor.generate_syllabus_overview(
                self.document_type,
                self.sections
            )
            return f"## Overview\n\n{overview}"
        except Exception as e:
            print(f"Warning: Could not generate overview: {e}")
            return ""
    
    def _generate_toc(self) -> str:
        """Generate table of contents"""
        toc = ["## TABLE OF CONTENTS\n"]
        
        for idx, topic in enumerate(self.index):
            toc.append(f"{idx + 1}. {topic}")
        
        toc.append("\n**Note**: Each section includes detailed explanations, equations, and animation suggestions.")
        return "\n".join(toc)
    
    def _generate_sections(self) -> str:
        """Generate all detailed sections"""
        sections_output = ["## DETAILED TEACHING SECTIONS\n"]
        
        for idx, section in enumerate(self.sections):
            print(f"Processing section {idx + 1}/{len(self.sections)}: {section.get('title', 'Untitled')}...")
            section_text = self._format_section(section)
            sections_output.append(section_text)
            sections_output.append("\n---\n")  # Separator between sections
        
        return "\n".join(sections_output)
    
    def _format_section(self, section: Dict[str, Any]) -> str:
        """
        Format individual section with AI enhancement
        
        Args:
            section: Section dictionary
        """
        section_id = section.get("id", 0)
        title = section.get("title", "Untitled")
        content = section.get("content", {})
        
        output = [
            f"### Section {section_id + 1}: {title}",
            ""
        ]
        
        # Get AI-enhanced content if professor available
        if self.professor:
            enhanced = self._get_enhanced_content(title, content)
            output.append(enhanced)
        else:
            # Fallback to basic formatting
            output.append(self._format_basic_content(content))
            output.append(self._generate_basic_animation_hints(title))
        
        return "\n".join(output)
    
    def _get_enhanced_content(self, title: str, content: Any) -> str:
        """Get AI-enhanced content from professor"""
        try:
            enhanced = self.professor.enhance_section(title, content)
            
            # Format the enhanced content
            formatted = []
            
            # Full professor response
            if enhanced.get('full_content'):
                formatted.append(enhanced['full_content'])
            
            # Add Manim-specific notes if we extracted them
            equations = enhanced.get('equations', [])
            if equations:
                formatted.append("\n#### Equations for Manim\n")
                for eq in equations:
                    manim_eq = format_equation_for_manim(eq)
                    formatted.append(f"```python\nMathTex(r\"{manim_eq}\")\n```\n")
            
            return "\n".join(formatted)
            
        except Exception as e:
            print(f"  Warning: Enhancement failed for '{title}': {e}")
            return self._format_basic_content(content)
    
    def _format_basic_content(self, content: Any) -> str:
        """Basic content formatting without AI"""
        if isinstance(content, dict):
            return self._parse_content_dict(content)
        elif isinstance(content, list):
            return self._parse_content_list(content)
        else:
            return f"**Content**: {content}"
    
    def _parse_content_dict(self, content: Dict[str, Any]) -> str:
        """Parse dictionary content"""
        parsed = []
        
        for key, value in content.items():
            formatted_key = key.replace("_", " ").title()
            
            if isinstance(value, list):
                parsed.append(f"**{formatted_key}**:")
                for item in value:
                    parsed.append(f"  - {item}")
            elif isinstance(value, dict):
                parsed.append(f"**{formatted_key}**:")
                for sub_key, sub_value in value.items():
                    parsed.append(f"  - {sub_key}: {sub_value}")
            else:
                parsed.append(f"**{formatted_key}**: {value}")
        
        return "\n".join(parsed)
    
    def _parse_content_list(self, content: List[Any]) -> str:
        """Parse list content"""
        parsed = ["**Content Items**:"]
        for idx, item in enumerate(content):
            if isinstance(item, dict):
                parsed.append(f"{idx + 1}. {json.dumps(item)}")
            else:
                parsed.append(f"{idx + 1}. {item}")
        return "\n".join(parsed)
    
    def _generate_basic_animation_hints(self, title: str) -> str:
        """Generate basic animation hints (fallback)"""
        return f"""
#### Animation Suggestions

- **Visual Style**: Clean, professional presentation
- **Introduction**: Fade in title "{title}"
- **Content Display**: Use Write or FadeIn for text
- **Emphasis**: Highlight key terms with color changes
- **Transitions**: Use smooth fade or slide transitions
- **Pacing**: 3-5 seconds per major point
"""
    
    def _generate_footer(self) -> str:
        """Generate footer with metadata"""
        footer = f"""
---

## Production Notes

**Generated with**: Manim-MCP Syllabus Generator  
**AI Enhancement**: {'Enabled ✓' if self.use_professor else 'Disabled'}  
**Format**: Markdown with LaTeX  

### Next Steps

1. **Review Content**: Check all sections for accuracy and completeness
2. **Refine Animations**: Adjust animation suggestions based on your style
3. **Generate Manim Code**: Use Scene Animator to create Python scripts
4. **Render Video**: Execute Manim to produce animations
5. **Add Narration**: Record and sync audio with animations

---
"""
        return footer
    
    def save_to_file(self, output_path: str) -> None:
        """Save generated syllabus to file"""
        syllabus = self.generate_syllabus()
        Path(output_path).write_text(syllabus, encoding='utf-8')
        print(f"✅ Syllabus saved to: {output_path}")


def convert_json_to_syllabus(
    json_input: str,
    output_path: str = None,
    use_professor: bool = True,
    config_path: str = None,
    api_key: str = None
) -> str:
    """
    Main conversion function
    
    Args:
        json_input: JSON string or file path
        output_path: Optional path to save output
        use_professor: Whether to use AI professor enhancement
        config_path: Path to config file
        api_key: OpenAI API key
    
    Returns:
        Generated syllabus string
    """
    # Load config
    config = {}
    if config_path:
        try:
            config = load_config(config_path)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
    else:
        try:
            config = load_config()  # Try default location
        except:
            pass
    
    # Load JSON data
    if not json_input.strip().startswith('{') and not json_input.strip().startswith('['):
        try:
            if Path(json_input).exists():
                with open(json_input, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = json.loads(json_input)
        except (OSError, json.JSONDecodeError):
            data = json.loads(json_input)
    else:
        data = json.loads(json_input)
    
    # Generate syllabus
    generator = SyllabusGenerator(
        data,
        use_professor=use_professor,
        config=config,
        api_key=api_key
    )
    syllabus = generator.generate_syllabus()
    
    # Save if output path provided
    if output_path:
        generator.save_to_file(output_path)
    
    return syllabus

