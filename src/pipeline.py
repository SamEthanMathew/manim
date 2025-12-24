"""
End-to-End Pipeline: PDF → JSON → Teaching Syllabus
Integrates TextExtractor and Syllabus Generator
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import sys

from text_extractor import extract_syllabus, extract_notes
from core.syllabus_generator import convert_json_to_syllabus


class ManimMCPPipeline:
    """Complete pipeline from PDF to teaching syllabus"""
    
    def __init__(
        self,
        use_professor: bool = True,
        config: Dict[str, Any] = None,
        api_key: str = None
    ):
        """
        Initialize the pipeline
        
        Args:
            use_professor: Enable AI enhancement
            config: Configuration dictionary
            api_key: OpenAI API key
        """
        self.use_professor = use_professor
        self.config = config
        self.api_key = api_key
    
    def process_pdf(
        self,
        pdf_path: str,
        output_path: str = None,
        document_type: str = "syllabus",
        save_json: bool = True
    ) -> str:
        """
        Complete pipeline: PDF → JSON → Teaching Syllabus
        
        Args:
            pdf_path: Path to input PDF file
            output_path: Path for output syllabus (optional)
            document_type: Type of document ("syllabus" or "notes")
            save_json: Whether to save intermediate JSON
            
        Returns:
            Generated teaching syllabus as string
        """
        print(f"🎓 Manim-MCP Complete Pipeline")
        print(f"   Input PDF: {pdf_path}")
        print(f"   Document Type: {document_type}")
        print()
        
        # Step 1: Extract text from PDF → JSON
        print("📄 Step 1: Extracting text from PDF...")
        
        json_path = None
        if save_json:
            pdf_name = Path(pdf_path).stem
            json_path = f"output/{pdf_name}_extracted.json"
        
        if document_type.lower() == "syllabus":
            json_data = extract_syllabus(pdf_path, json_path)
        elif document_type.lower() == "notes":
            json_data = extract_notes(pdf_path, json_path)
        else:
            raise ValueError(f"Unknown document type: {document_type}")
        
        print(f"   ✓ Extracted {len(json_data.get('sections', []))} sections")
        
        if json_path:
            print(f"   ✓ Saved JSON to: {json_path}")
        
        # Step 2: Convert JSON → Teaching Syllabus
        print()
        print("🎨 Step 2: Generating teaching syllabus...")
        
        syllabus = convert_json_to_syllabus(
            json.dumps(json_data),
            output_path=output_path,
            use_professor=self.use_professor,
            config_path=None,  # Use default config
            api_key=self.api_key
        )
        
        print()
        print("✅ Pipeline complete!")
        
        if output_path:
            print(f"   📝 Syllabus: {output_path}")
        if json_path:
            print(f"   📦 JSON: {json_path}")
        
        return syllabus
    
    def process_json(
        self,
        json_path: str,
        output_path: str = None
    ) -> str:
        """
        Process existing JSON file → Teaching Syllabus
        
        Args:
            json_path: Path to JSON file
            output_path: Path for output syllabus
            
        Returns:
            Generated teaching syllabus
        """
        print(f"🎓 Manim-MCP Pipeline (JSON → Syllabus)")
        print(f"   Input JSON: {json_path}")
        print()
        
        syllabus = convert_json_to_syllabus(
            json_path,
            output_path=output_path,
            use_professor=self.use_professor,
            config_path=None,
            api_key=self.api_key
        )
        
        print()
        print("✅ Syllabus generated!")
        if output_path:
            print(f"   📝 Output: {output_path}")
        
        return syllabus


def pdf_to_syllabus(
    pdf_path: str,
    output_path: str = None,
    document_type: str = "syllabus",
    use_ai: bool = True,
    api_key: str = None
) -> str:
    """
    Convenience function: PDF → Teaching Syllabus in one call
    
    Args:
        pdf_path: Path to PDF file
        output_path: Where to save syllabus
        document_type: "syllabus" or "notes"
        use_ai: Enable AI Professor enhancement
        api_key: OpenAI API key
        
    Returns:
        Generated syllabus string
    """
    pipeline = ManimMCPPipeline(
        use_professor=use_ai,
        api_key=api_key
    )
    
    return pipeline.process_pdf(
        pdf_path,
        output_path=output_path,
        document_type=document_type
    )


# Example usage
if __name__ == "__main__":
    import os
    
    # Test with the example PDFs
    test_files = [
        ("src/text_extractor/testfiles/DiscreteMath_Syllabus.pdf", "syllabus"),
        ("src/text_extractor/testfiles/DiscreteMath_Combinatronics.pdf", "notes")
    ]
    
    print("=" * 60)
    print("Testing Manim-MCP Complete Pipeline")
    print("=" * 60)
    print()
    
    for pdf_file, doc_type in test_files:
        if not Path(pdf_file).exists():
            print(f"⚠️  File not found: {pdf_file}")
            continue
        
        pdf_name = Path(pdf_file).stem
        output_file = f"output/pipeline_{pdf_name}_syllabus.md"
        
        try:
            syllabus = pdf_to_syllabus(
                pdf_file,
                output_path=output_file,
                document_type=doc_type,
                use_ai=bool(os.getenv('OPENAI_API_KEY'))
            )
            
            print()
            print(f"Preview (first 500 chars):")
            print(syllabus[:500])
            print("...\n")
            
        except Exception as e:
            print(f"❌ Error processing {pdf_file}: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        print("-" * 60)
        print()

