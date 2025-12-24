"""
AI Professor Agent using OpenAI
Generates rich teaching content with LaTeX equations and animation suggestions
"""

import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
import os


class ProfessorAgent:
    """AI Professor that generates educational content using OpenAI"""
    
    def __init__(self, config: Dict[str, Any] = None, api_key: str = None):
        """
        Initialize Professor Agent
        
        Args:
            config: Configuration dictionary
            api_key: OpenAI API key (or from environment)
        """
        self.config = config or {}
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=self.api_key)
        
        # Load settings from config
        openai_config = self.config.get('openai', {})
        professor_config = self.config.get('professor', {})
        
        self.model = openai_config.get('model', 'gpt-4o')
        self.temperature = openai_config.get('temperature', 0.7)
        self.max_tokens = openai_config.get('max_tokens', 4000)
        self.system_prompt = professor_config.get('system_prompt', self._default_system_prompt())
        self.use_web_search = professor_config.get('use_web_search', True)
    
    def _default_system_prompt(self) -> str:
        """Default system prompt for the professor"""
        return """You are an expert educational content creator and professor. Your role is to:
1. Create comprehensive teaching content with clear explanations
2. Include relevant mathematical equations in LaTeX format (use $ for inline, $$ for block)
3. Suggest specific animation ideas for visual representation in Manim
4. Break down complex topics into digestible segments
5. Provide context and real-world applications
6. Recommend pacing and emphasis for educational videos

Format your responses in Markdown with LaTeX equations.
Always think about how concepts can be visualized in animations.
Be specific about animation suggestions (e.g., "fade in text", "morph equation", "highlight terms").
"""
    
    def enhance_section(
        self,
        title: str,
        content: Any,
        context: str = ""
    ) -> Dict[str, str]:
        """
        Enhance a section with rich teaching content
        
        Args:
            title: Section title
            content: Section content (can be dict, list, or string)
            context: Additional context about the topic
            
        Returns:
            Dictionary with enhanced content:
                - explanation: Detailed explanation
                - equations: LaTeX equations
                - animation_ideas: Specific animation suggestions
                - key_points: Main takeaways
        """
        prompt = self._build_enhancement_prompt(title, content, context)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            result = response.choices[0].message.content
            return self._parse_response(result)
            
        except Exception as e:
            print(f"Warning: Professor enhancement failed: {e}")
            return self._fallback_response(title, content)
    
    def _build_enhancement_prompt(self, title: str, content: Any, context: str) -> str:
        """Build prompt for content enhancement"""
        content_str = self._format_content_for_prompt(content)
        
        prompt = f"""Create comprehensive teaching content for this section:

**Topic**: {title}
**Content**: {content_str}
{f'**Context**: {context}' if context else ''}

Please provide:

1. **Detailed Explanation**: A clear, engaging explanation suitable for educational video narration
2. **Key Concepts**: Main ideas and definitions
3. **Mathematical Formulas** (if applicable): Include relevant equations in LaTeX format
4. **Real-World Applications**: Practical examples or use cases
5. **Animation Suggestions**: Specific ideas for Manim animations:
   - Visual metaphors or diagrams
   - How to introduce concepts
   - Transitions and effects
   - Color coding or highlighting
   - Step-by-step reveals
6. **Pacing Notes**: Recommended timing and emphasis

Format your response with clear Markdown sections.
Use $ for inline math and $$ for display equations.
Be specific and actionable in animation suggestions.
"""
        return prompt
    
    def _format_content_for_prompt(self, content: Any) -> str:
        """Format content for inclusion in prompt"""
        if isinstance(content, dict):
            return json.dumps(content, indent=2)
        elif isinstance(content, list):
            return "\n".join(f"- {item}" for item in content)
        else:
            return str(content)
    
    def _parse_response(self, response: str) -> Dict[str, str]:
        """Parse LLM response into structured format"""
        # For now, return the full response as explanation
        # In future, could parse sections more intelligently
        return {
            "full_content": response,
            "explanation": self._extract_section(response, "Explanation", "Key Concepts"),
            "key_concepts": self._extract_section(response, "Key Concepts", "Mathematical"),
            "equations": self._extract_equations(response),
            "animation_ideas": self._extract_section(response, "Animation", "Pacing"),
            "pacing_notes": self._extract_section(response, "Pacing", None)
        }
    
    def _extract_section(self, text: str, start_marker: str, end_marker: Optional[str]) -> str:
        """Extract a section from markdown text"""
        import re
        
        # Find section starting with marker
        pattern = rf"(?:^|\n).*{start_marker}.*?:?\s*\n(.*?)(?=\n.*(?:{end_marker}|$))" if end_marker else rf"(?:^|\n).*{start_marker}.*?:?\s*\n(.*)"
        
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_equations(self, text: str) -> List[str]:
        """Extract LaTeX equations from text"""
        import re
        equations = []
        
        # Block equations
        for match in re.finditer(r'\$\$(.*?)\$\$', text, re.DOTALL):
            equations.append(match.group(1).strip())
        
        # Inline equations
        for match in re.finditer(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', text):
            equations.append(match.group(1).strip())
        
        return equations
    
    def _fallback_response(self, title: str, content: Any) -> Dict[str, str]:
        """Fallback response if API call fails"""
        return {
            "full_content": f"## {title}\n\n{content}",
            "explanation": str(content),
            "key_concepts": "",
            "equations": [],
            "animation_ideas": "Display content with fade-in animation",
            "pacing_notes": "Allow 3-5 seconds per point"
        }
    
    def generate_syllabus_overview(
        self,
        document_type: str,
        sections: List[Dict[str, Any]]
    ) -> str:
        """
        Generate an overview/introduction for the entire syllabus
        
        Args:
            document_type: Type of document (syllabus, lecture, etc.)
            sections: List of all sections
            
        Returns:
            Markdown-formatted overview
        """
        section_titles = [s.get('title', '') for s in sections]
        
        prompt = f"""Create an engaging introduction for an educational video about this {document_type}.

**Topics to be covered**:
{chr(10).join(f'- {title}' for title in section_titles)}

Provide:
1. A brief, engaging introduction (2-3 sentences)
2. Learning objectives
3. Overall structure and flow
4. Suggested opening animation (e.g., title reveal, topic preview)

Keep it concise and video-friendly.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Warning: Overview generation failed: {e}")
            return f"# {document_type.title()}\n\nCovering: {', '.join(section_titles)}"
    
    def suggest_visual_style(self, topic: str, content_type: str = "educational") -> Dict[str, Any]:
        """
        Suggest visual style and color schemes for animations
        
        Args:
            topic: The main topic
            content_type: Type of content (educational, technical, etc.)
            
        Returns:
            Dictionary with visual suggestions
        """
        prompt = f"""Suggest a visual style for a Manim animation about: {topic}

Provide:
1. Color palette (3-5 colors with hex codes)
2. Animation style (modern, classic, minimalist, etc.)
3. Font suggestions
4. Layout recommendations
5. Visual motifs or themes

Format as JSON.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert in visual design for educational content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            # Try to parse as JSON, fallback to text
            try:
                return json.loads(content)
            except:
                return {"description": content}
                
        except Exception as e:
            print(f"Warning: Visual style suggestion failed: {e}")
            return {
                "color_palette": ["#3498db", "#2ecc71", "#e74c3c"],
                "style": "modern",
                "description": "Use clean, modern visuals with blue as primary color"
            }

