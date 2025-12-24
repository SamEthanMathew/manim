"""
PDF Extraction System for Manim Integration

This module provides flexible PDF extraction capabilities using pdfplumber,
with automatic structure detection and hierarchical JSON output.
"""

import pdfplumber
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import re


class PDFExtractor:
    """Base class for PDF processing with pdfplumber."""
    
    def __init__(self, pdf_path: str):
        """
        Initialize the PDF extractor.
        
        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        self.pdf = None
        self.pages = []
        self.raw_text = ""
        self.metadata = {}
        
    def __enter__(self):
        """Context manager entry."""
        self.pdf = pdfplumber.open(self.pdf_path)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.pdf:
            self.pdf.close()
            
    def extract_text(self) -> str:
        """Extract all text from the PDF."""
        if not self.pdf:
            raise ValueError("PDF not opened. Use context manager.")
            
        text_parts = []
        for page in self.pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
                
        self.raw_text = "\n".join(text_parts)
        return self.raw_text
        
    def extract_text_with_formatting(self) -> List[Dict[str, Any]]:
        """
        Extract text with formatting information (font, size, position).
        
        Returns:
            List of text elements with formatting data
        """
        if not self.pdf:
            raise ValueError("PDF not opened. Use context manager.")
            
        formatted_text = []
        
        for page_num, page in enumerate(self.pdf.pages):
            # Extract words with their properties
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=True
            )
            
            for word in words:
                formatted_text.append({
                    'text': word['text'],
                    'page': page_num + 1,
                    'x0': word['x0'],
                    'y0': word['top'],
                    'x1': word['x1'],
                    'y1': word['bottom'],
                    'fontname': word.get('fontname', ''),
                    'size': word.get('size', 0),
                    'height': word.get('height', 0)
                })
                
        return formatted_text
        
    def extract_tables(self) -> List[Dict[str, Any]]:
        """
        Extract tables from the PDF.
        
        Returns:
            List of tables with their data and page numbers
        """
        if not self.pdf:
            raise ValueError("PDF not opened. Use context manager.")
            
        tables_data = []
        
        for page_num, page in enumerate(self.pdf.pages):
            tables = page.extract_tables()
            for table_idx, table in enumerate(tables):
                if table:
                    tables_data.append({
                        'page': page_num + 1,
                        'table_index': table_idx,
                        'data': table,
                        'rows': len(table),
                        'cols': len(table[0]) if table else 0
                    })
                    
        return tables_data
        
    def get_metadata(self) -> Dict[str, Any]:
        """Extract PDF metadata."""
        if not self.pdf:
            raise ValueError("PDF not opened. Use context manager.")
            
        self.metadata = {
            'filename': self.pdf_path.name,
            'num_pages': len(self.pdf.pages),
            'metadata': self.pdf.metadata or {}
        }
        
        return self.metadata


class StructureDetector:
    """Analyzes document structure to identify headings and sections."""
    
    def __init__(self, formatted_text: List[Dict[str, Any]], 
                 font_size_threshold: float = 1.2,
                 position_threshold: float = 50.0):
        """
        Initialize the structure detector.
        
        Args:
            formatted_text: Text with formatting information
            font_size_threshold: Ratio for detecting larger fonts (headings)
            position_threshold: X-position threshold for left-aligned headings
        """
        self.formatted_text = formatted_text
        self.font_size_threshold = font_size_threshold
        self.position_threshold = position_threshold
        self.font_sizes = []
        self.analyze_fonts()
        
    def analyze_fonts(self):
        """Analyze font sizes in the document."""
        sizes = [item['size'] for item in self.formatted_text if item['size'] > 0]
        self.font_sizes = sorted(set(sizes), reverse=True)
        
        # Calculate base font size (most common)
        size_counts = defaultdict(int)
        for size in sizes:
            size_counts[size] += 1
            
        if size_counts:
            self.base_font_size = max(size_counts.items(), key=lambda x: x[1])[0]
        else:
            self.base_font_size = 10.0
            
    def group_into_lines(self) -> List[Dict[str, Any]]:
        """Group words into lines based on vertical position."""
        if not self.formatted_text:
            return []
            
        # Sort by page and vertical position
        sorted_text = sorted(self.formatted_text, 
                           key=lambda x: (x['page'], x['y0']))
        
        lines = []
        current_line = []
        current_y = None
        current_page = None
        y_tolerance = 3
        
        for item in sorted_text:
            if (current_page is None or 
                item['page'] != current_page or 
                current_y is None or 
                abs(item['y0'] - current_y) > y_tolerance):
                
                # Start new line
                if current_line:
                    lines.append(self._merge_line(current_line))
                    
                current_line = [item]
                current_y = item['y0']
                current_page = item['page']
            else:
                # Continue current line
                current_line.append(item)
                
        # Add last line
        if current_line:
            lines.append(self._merge_line(current_line))
            
        return lines
        
    def _merge_line(self, words: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge words into a single line object."""
        # Sort words by x position
        words = sorted(words, key=lambda x: x['x0'])
        
        text = ' '.join(word['text'] for word in words)
        
        # Use the most common/largest font size in the line
        sizes = [w['size'] for w in words if w['size'] > 0]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        max_size = max(sizes) if sizes else 0
        
        return {
            'text': text,
            'page': words[0]['page'],
            'x0': min(w['x0'] for w in words),
            'y0': min(w['y0'] for w in words),
            'x1': max(w['x1'] for w in words),
            'y1': max(w['y1'] for w in words),
            'size': max_size,
            'avg_size': avg_size,
            'fontname': words[0].get('fontname', '')
        }
        
    def detect_headings(self) -> List[Dict[str, Any]]:
        """
        Detect headings based on font size, position, and patterns.
        
        Returns:
            List of detected headings with their properties
        """
        lines = self.group_into_lines()
        headings = []
        
        for idx, line in enumerate(lines):
            is_heading = False
            heading_level = 0
            confidence = 0.0
            reasons = []
            
            # Font size analysis
            if line['size'] > self.base_font_size * self.font_size_threshold:
                is_heading = True
                size_ratio = line['size'] / self.base_font_size
                heading_level = max(1, int(3 - size_ratio))
                confidence += 0.4
                reasons.append('large_font')
                
            # Position analysis (left-aligned, good spacing)
            if line['x0'] < self.position_threshold:
                confidence += 0.2
                reasons.append('left_aligned')
                
            # Pattern analysis
            text = line['text'].strip()
            
            # Numbered sections (1., 1.1, etc.)
            if re.match(r'^\d+\.(\d+\.)*\s+\w+', text):
                is_heading = True
                confidence += 0.5
                reasons.append('numbered')
                heading_level = text.count('.')
                
            # ALL CAPS short text
            if text.isupper() and len(text.split()) <= 10:
                is_heading = True
                confidence += 0.3
                reasons.append('all_caps')
                if heading_level == 0:
                    heading_level = 2
                    
            # Short text (potential heading)
            if len(text.split()) <= 8 and len(text) < 80:
                confidence += 0.1
                reasons.append('short_text')
                
            # Title case for short text
            if text.istitle() and len(text.split()) <= 10:
                confidence += 0.2
                reasons.append('title_case')
                
            if is_heading and confidence >= 0.3:
                headings.append({
                    'text': text,
                    'page': line['page'],
                    'level': max(1, heading_level),
                    'confidence': min(1.0, confidence),
                    'line_index': idx,
                    'reasons': reasons,
                    'y_position': line['y0']
                })
                
        return headings


class HierarchyBuilder:
    """Builds nested JSON structure from detected sections."""
    
    def __init__(self, lines: List[Dict[str, Any]], 
                 headings: List[Dict[str, Any]]):
        """
        Initialize the hierarchy builder.
        
        Args:
            lines: All text lines from the document
            headings: Detected headings
        """
        self.lines = lines
        self.headings = sorted(headings, key=lambda x: x['line_index'])
        
    def build_hierarchy(self) -> Dict[str, Any]:
        """
        Build hierarchical structure with sections and content.
        
        Returns:
            Nested dictionary representing document structure
        """
        if not self.headings:
            # No headings detected, return all content as single section
            return {
                'sections': [{
                    'id': 0,
                    'title': 'Content',
                    'content': '\n'.join(line['text'] for line in self.lines),
                    'page_start': self.lines[0]['page'] if self.lines else 1,
                    'page_end': self.lines[-1]['page'] if self.lines else 1
                }],
                'index': ['Content']
            }
            
        sections = []
        index = []
        
        for i, heading in enumerate(self.headings):
            # Determine content range
            start_line = heading['line_index'] + 1
            end_line = (self.headings[i + 1]['line_index'] 
                       if i + 1 < len(self.headings) 
                       else len(self.lines))
            
            # Extract content between this heading and next
            content_lines = self.lines[start_line:end_line]
            content_text = '\n'.join(line['text'] for line in content_lines)
            
            section = {
                'id': i,
                'title': heading['text'],
                'level': heading['level'],
                'content': content_text.strip(),
                'page_start': heading['page'],
                'page_end': content_lines[-1]['page'] if content_lines else heading['page'],
                'confidence': heading['confidence']
            }
            
            sections.append(section)
            index.append(heading['text'])
            
        return {
            'sections': sections,
            'index': index
        }
        
    def build_nested_hierarchy(self) -> Dict[str, Any]:
        """
        Build hierarchical structure with nested subsections.
        
        Returns:
            Nested dictionary with parent-child relationships
        """
        if not self.headings:
            return self.build_hierarchy()
            
        # Build flat structure first
        flat = self.build_hierarchy()
        sections = flat['sections']
        
        # Create nested structure
        root_sections = []
        stack = []
        
        for section in sections:
            # Remove sections from stack with same or lower level
            while stack and stack[-1]['level'] >= section['level']:
                stack.pop()
                
            if not stack:
                # Root level section
                root_sections.append(section)
                section['subsections'] = []
                stack.append(section)
            else:
                # Child section
                parent = stack[-1]
                if 'subsections' not in parent:
                    parent['subsections'] = []
                parent['subsections'].append(section)
                section['subsections'] = []
                stack.append(section)
                
        return {
            'sections': root_sections,
            'index': flat['index']
        }


class SyllabusExtractor(PDFExtractor):
    """Specialized extractor for syllabus PDFs."""
    
    def extract(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract syllabus information in structured format.
        
        Args:
            output_path: Optional path to save JSON output
            
        Returns:
            Structured syllabus data
        """
        # Extract formatted text
        formatted_text = self.extract_text_with_formatting()
        
        # Detect structure
        detector = StructureDetector(formatted_text)
        lines = detector.group_into_lines()
        headings = detector.detect_headings()
        
        # Build hierarchy
        builder = HierarchyBuilder(lines, headings)
        hierarchy = builder.build_nested_hierarchy()
        
        # Extract tables
        tables = self.extract_tables()
        
        # Get metadata
        metadata = self.get_metadata()
        
        # Build syllabus structure
        result = {
            'document_type': 'syllabus',
            'metadata': metadata,
            'index': hierarchy['index'],
            'sections': hierarchy['sections'],
            'tables': tables
        }
        
        # Save to file if path provided
        if output_path:
            self._save_json(result, output_path)
            
        return result
        
    def _save_json(self, data: Dict[str, Any], path: str):
        """Save data to JSON file."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class NotesExtractor(PDFExtractor):
    """Specialized extractor for lecture notes PDFs."""
    
    def extract(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract notes information with topic/subtopic hierarchy.
        
        Args:
            output_path: Optional path to save JSON output
            
        Returns:
            Structured notes data
        """
        # Extract formatted text
        formatted_text = self.extract_text_with_formatting()
        
        # Detect structure
        detector = StructureDetector(
            formatted_text,
            font_size_threshold=1.15,  # More sensitive for notes
            position_threshold=60.0
        )
        lines = detector.group_into_lines()
        headings = detector.detect_headings()
        
        # Build hierarchy
        builder = HierarchyBuilder(lines, headings)
        hierarchy = builder.build_nested_hierarchy()
        
        # Extract tables
        tables = self.extract_tables()
        
        # Get metadata
        metadata = self.get_metadata()
        
        # Detect main topic from first heading or filename
        main_topic = (headings[0]['text'] if headings 
                     else self.pdf_path.stem.replace('_', ' '))
        
        # Build notes structure
        result = {
            'document_type': 'notes',
            'main_topic': main_topic,
            'metadata': metadata,
            'index': hierarchy['index'],
            'sections': hierarchy['sections'],
            'tables': tables
        }
        
        # Save to file if path provided
        if output_path:
            self._save_json(result, output_path)
            
        return result
        
    def _save_json(self, data: Dict[str, Any], path: str):
        """Save data to JSON file."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def extract_syllabus(pdf_path: str, output_path: str) -> Dict[str, Any]:
    """
    Convenience function to extract syllabus.
    
    Args:
        pdf_path: Path to syllabus PDF
        output_path: Path for JSON output
        
    Returns:
        Extracted syllabus data
    """
    with SyllabusExtractor(pdf_path) as extractor:
        return extractor.extract(output_path)


def extract_notes(pdf_path: str, output_path: str) -> Dict[str, Any]:
    """
    Convenience function to extract notes.
    
    Args:
        pdf_path: Path to notes PDF
        output_path: Path for JSON output
        
    Returns:
        Extracted notes data
    """
    with NotesExtractor(pdf_path) as extractor:
        return extractor.extract(output_path)


class LaTeXConverter:
    """Converts extracted JSON data to LaTeX format."""
    
    @staticmethod
    def escape_latex(text: str) -> str:
        """
        Escape special LaTeX characters in text.
        
        Args:
            text: Text to escape
            
        Returns:
            LaTeX-safe text
        """
        if not text:
            return ""
        
        # Basic LaTeX character escaping
        replacements = {
            '\\': r'\textbackslash{}',
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
        }
        
        # Apply replacements
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text
    
    @staticmethod
    def section_to_latex(section: Dict[str, Any], level: int = 0, escape: bool = True) -> str:
        """
        Convert a section to LaTeX format.
        
        Args:
            section: Section dictionary
            level: Nesting level for determining section command
            escape: Whether to escape LaTeX special characters
            
        Returns:
            LaTeX formatted section
        """
        latex_lines = []
        
        # Determine section command based on level
        section_commands = ['section', 'subsection', 'subsubsection', 'paragraph', 'subparagraph']
        section_level = min(section.get('level', 1) - 1 + level, len(section_commands) - 1)
        section_cmd = section_commands[section_level]
        
        # Add section title
        title = section.get('title', 'Untitled')
        if escape and not LaTeXConverter._is_latex_code(title):
            title = LaTeXConverter.escape_latex(title)
        
        latex_lines.append(f"\\{section_cmd}{{{title}}}")
        latex_lines.append("")
        
        # Add content
        content = section.get('content', '').strip()
        if content:
            if escape and not LaTeXConverter._is_latex_code(content):
                content = LaTeXConverter.escape_latex(content)
            latex_lines.append(content)
            latex_lines.append("")
        
        # Process subsections recursively
        if 'subsections' in section and section['subsections']:
            for subsection in section['subsections']:
                latex_lines.append(LaTeXConverter.section_to_latex(subsection, level, escape))
                latex_lines.append("")
        
        return '\n'.join(latex_lines)
    
    @staticmethod
    def _is_latex_code(text: str) -> bool:
        """
        Check if text appears to contain LaTeX code.
        
        Args:
            text: Text to check
            
        Returns:
            True if text appears to be LaTeX code
        """
        # Simple heuristic: if text contains LaTeX commands, assume it's already LaTeX
        latex_indicators = ['\\begin{', '\\end{', '\\section', '\\subsection', '\\text']
        return any(indicator in text for indicator in latex_indicators)
    
    @staticmethod
    def table_to_latex(table: Dict[str, Any]) -> str:
        """
        Convert a table to LaTeX tabular format.
        
        Args:
            table: Table dictionary with 'data' field
            
        Returns:
            LaTeX formatted table
        """
        if not table or 'data' not in table or not table['data']:
            return ""
        
        data = table['data']
        num_cols = table.get('cols', len(data[0]) if data else 0)
        
        latex_lines = []
        latex_lines.append("\\begin{table}[h]")
        latex_lines.append("\\centering")
        latex_lines.append(f"\\begin{{tabular}}{{{'|'.join(['l'] * num_cols)}}}")
        latex_lines.append("\\hline")
        
        for row in data:
            if row:  # Skip empty rows
                # Clean and escape cell content
                cells = []
                for cell in row:
                    if cell is None:
                        cell = ""
                    cell_text = str(cell).strip()
                    if not LaTeXConverter._is_latex_code(cell_text):
                        cell_text = LaTeXConverter.escape_latex(cell_text)
                    cells.append(cell_text)
                
                latex_lines.append(" & ".join(cells) + " \\\\")
                latex_lines.append("\\hline")
        
        latex_lines.append("\\end{tabular}")
        latex_lines.append("\\end{table}")
        
        return '\n'.join(latex_lines)


def json_to_latex_syllabus(json_path: str, output_path: str, 
                           document_class: str = "article",
                           include_preamble: bool = True) -> str:
    """
    Convert syllabus JSON to LaTeX format.
    
    Args:
        json_path: Path to syllabus JSON file
        output_path: Path for LaTeX output
        document_class: LaTeX document class
        include_preamble: Whether to include full LaTeX document preamble
        
    Returns:
        LaTeX formatted content
    """
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    latex_lines = []
    
    # Add preamble if requested
    if include_preamble:
        latex_lines.extend([
            f"\\documentclass{{{document_class}}}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage{amsmath}",
            "\\usepackage{amssymb}",
            "\\usepackage{hyperref}",
            "\\usepackage{geometry}",
            "\\geometry{margin=1in}",
            "",
            "\\title{" + LaTeXConverter.escape_latex(data.get('metadata', {}).get('filename', 'Syllabus')) + "}",
            "\\date{\\today}",
            "",
            "\\begin{document}",
            "\\maketitle",
            "\\tableofcontents",
            "\\newpage",
            ""
        ])
    
    # Add sections
    for section in data.get('sections', []):
        latex_lines.append(LaTeXConverter.section_to_latex(section, level=0, escape=True))
        latex_lines.append("")
    
    # Add tables if present
    if data.get('tables'):
        latex_lines.append("\\section{Tables}")
        latex_lines.append("")
        for i, table in enumerate(data['tables']):
            latex_lines.append(f"% Table {i+1} from page {table.get('page', 'unknown')}")
            latex_lines.append(LaTeXConverter.table_to_latex(table))
            latex_lines.append("")
    
    # Close document if preamble was included
    if include_preamble:
        latex_lines.append("\\end{document}")
    
    latex_content = '\n'.join(latex_lines)
    
    # Save to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(latex_content)
    
    return latex_content


def json_to_latex_notes(json_path: str, output_path: str,
                        document_class: str = "article",
                        include_preamble: bool = True) -> str:
    """
    Convert notes JSON to LaTeX format.
    
    Args:
        json_path: Path to notes JSON file
        output_path: Path for LaTeX output
        document_class: LaTeX document class
        include_preamble: Whether to include full LaTeX document preamble
        
    Returns:
        LaTeX formatted content
    """
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    latex_lines = []
    
    # Add preamble if requested
    if include_preamble:
        main_topic = data.get('main_topic', 'Lecture Notes')
        if not LaTeXConverter._is_latex_code(main_topic):
            main_topic = LaTeXConverter.escape_latex(main_topic)
        
        latex_lines.extend([
            f"\\documentclass{{{document_class}}}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage{amsmath}",
            "\\usepackage{amssymb}",
            "\\usepackage{amsthm}",
            "\\usepackage{hyperref}",
            "\\usepackage{geometry}",
            "\\geometry{margin=1in}",
            "",
            "% Theorem environments",
            "\\newtheorem{theorem}{Theorem}",
            "\\newtheorem{lemma}{Lemma}",
            "\\newtheorem{definition}{Definition}",
            "\\newtheorem{example}{Example}",
            "",
            f"\\title{{{main_topic}}}",
            "\\date{\\today}",
            "",
            "\\begin{document}",
            "\\maketitle",
            "\\tableofcontents",
            "\\newpage",
            ""
        ])
    
    # Add sections
    for section in data.get('sections', []):
        latex_lines.append(LaTeXConverter.section_to_latex(section, level=0, escape=True))
        latex_lines.append("")
    
    # Add tables if present (less common in notes but handle it)
    if data.get('tables'):
        latex_lines.append("\\section{Tables}")
        latex_lines.append("")
        for i, table in enumerate(data['tables']):
            latex_lines.append(f"% Table {i+1} from page {table.get('page', 'unknown')}")
            latex_lines.append(LaTeXConverter.table_to_latex(table))
            latex_lines.append("")
    
    # Close document if preamble was included
    if include_preamble:
        latex_lines.append("\\end{document}")
    
    latex_content = '\n'.join(latex_lines)
    
    # Save to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(latex_content)
    
    return latex_content


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Set UTF-8 encoding for console output
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("PDF Extraction System")
    print("=" * 50)
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Extract syllabus
    print("\nExtracting syllabus...")
    syllabus_path = "testfiles/DiscreteMath_Syllabus.pdf"
    if Path(syllabus_path).exists():
        syllabus_data = extract_syllabus(
            syllabus_path,
            "output/syllabus.json"
        )
        print(f"[OK] Syllabus extracted: {len(syllabus_data['sections'])} sections found")
        # Handle encoding issues for preview
        index_preview = ', '.join(syllabus_data['index'][:3])
        if len(syllabus_data['index']) > 3:
            index_preview += "..."
        print(f"  Sections: {index_preview}")
    else:
        print(f"[ERROR] Syllabus file not found: {syllabus_path}")
    
    # Extract notes
    print("\nExtracting notes...")
    notes_path = "testfiles/DiscreteMath_Combinatronics.pdf"
    if Path(notes_path).exists():
        notes_data = extract_notes(
            notes_path,
            "output/notes.json"
        )
        print(f"[OK] Notes extracted: {len(notes_data['sections'])} sections found")
        print(f"  Main topic: {notes_data['main_topic']}")
        # Handle encoding issues for preview
        index_preview = str(len(notes_data['index'])) + " topics detected"
        print(f"  Index: {index_preview}")
    else:
        print(f"[ERROR] Notes file not found: {notes_path}")
    
    # Convert to LaTeX
    print("\n" + "=" * 50)
    print("Converting to LaTeX...")
    print("=" * 50)
    
    # Convert syllabus to LaTeX
    if Path("output/syllabus.json").exists():
        print("\nConverting syllabus to LaTeX...")
        json_to_latex_syllabus(
            "output/syllabus.json",
            "output/syllabus.tex"
        )
        print("[OK] Syllabus LaTeX saved to: output/syllabus.tex")
    
    # Convert notes to LaTeX
    if Path("output/notes.json").exists():
        print("\nConverting notes to LaTeX...")
        json_to_latex_notes(
            "output/notes.json",
            "output/notes.tex"
        )
        print("[OK] Notes LaTeX saved to: output/notes.tex")
    
    print("\n" + "=" * 50)
    print("Extraction complete! Check the 'output' directory for:")
    print("  - JSON files (structured data)")
    print("  - TEX files (LaTeX documents)")

