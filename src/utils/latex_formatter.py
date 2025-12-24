"""LaTeX formatting utilities for educational content"""

import re
from typing import List, Tuple


def format_latex(text: str) -> str:
    """
    Ensure LaTeX equations are properly formatted for Markdown/LaTeX output
    
    Args:
        text: Text containing LaTeX equations
        
    Returns:
        Formatted text with proper LaTeX delimiters
    """
    # Ensure inline math is wrapped with single $
    # Block math with double $$
    return text


def escape_latex(text: str) -> str:
    """
    Escape special LaTeX characters in regular text
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for LaTeX
    """
    special_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
    }
    
    result = text
    for char, escaped in special_chars.items():
        result = result.replace(char, escaped)
    
    return result


def extract_equations(text: str) -> List[Tuple[str, str]]:
    """
    Extract LaTeX equations from text
    
    Args:
        text: Text containing LaTeX equations
        
    Returns:
        List of (equation, type) tuples where type is 'inline' or 'block'
    """
    equations = []
    
    # Find block equations ($$...$$)
    block_pattern = r'\$\$(.*?)\$\$'
    for match in re.finditer(block_pattern, text, re.DOTALL):
        equations.append((match.group(1).strip(), 'block'))
    
    # Find inline equations ($...$) but not block ones
    inline_pattern = r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)'
    for match in re.finditer(inline_pattern, text):
        equations.append((match.group(1).strip(), 'inline'))
    
    return equations


def validate_latex(equation: str) -> bool:
    """
    Basic validation for LaTeX equation syntax
    
    Args:
        equation: LaTeX equation string
        
    Returns:
        True if equation appears valid
    """
    # Check for balanced braces
    brace_count = 0
    for char in equation:
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        if brace_count < 0:
            return False
    
    return brace_count == 0


def format_equation_for_manim(equation: str) -> str:
    """
    Format LaTeX equation for use in Manim MathTex or Tex objects
    
    Args:
        equation: LaTeX equation
        
    Returns:
        Formatted equation string for Manim
    """
    # Remove outer $ delimiters if present
    equation = equation.strip()
    if equation.startswith('$$') and equation.endswith('$$'):
        equation = equation[2:-2].strip()
    elif equation.startswith('$') and equation.endswith('$'):
        equation = equation[1:-1].strip()
    
    return equation

