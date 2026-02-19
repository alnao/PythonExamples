"""
Test script to verify formatting preservation in PDF translation.
This script creates a sample PDF with various formatting and translates it.
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import red, blue, green
from translator import PDFTranslator
import os


def create_test_pdf(output_path="test_input.pdf"):
    """Create a test PDF with various formatting."""
    print("Creating test PDF with formatting...")
    
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=blue
    )
    story.append(Paragraph("<b>Test Document for Translation</b>", title_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Normal text
    story.append(Paragraph("This is normal text in English.", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Bold text
    story.append(Paragraph("<b>This is bold text that should remain bold.</b>", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Italic text
    story.append(Paragraph("<i>This is italic text that should remain italic.</i>", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Bold and italic
    story.append(Paragraph("<b><i>This is bold and italic text.</i></b>", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Red text
    red_style = ParagraphStyle('RedText', parent=styles['Normal'], textColor=red)
    story.append(Paragraph("This is red text that should remain red.", red_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Green text
    green_style = ParagraphStyle('GreenText', parent=styles['Normal'], textColor=green)
    story.append(Paragraph("This is green text that should remain green.", green_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Multiple lines with different formatting
    story.append(Paragraph("Line 1: Regular text", styles['Normal']))
    story.append(Paragraph("<b>Line 2: Bold text</b>", styles['Normal']))
    story.append(Paragraph("<i>Line 3: Italic text</i>", styles['Normal']))
    red_line = ParagraphStyle('RedLine', parent=styles['Normal'], textColor=red)
    story.append(Paragraph("Line 4: Red text", red_line))
    story.append(Spacer(1, 0.3 * inch))
    
    # Technical content
    story.append(Paragraph("<b>Technical Section</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("The <b>Python</b> programming language supports <i>object-oriented</i> programming.", styles['Normal']))
    story.append(Paragraph("Variables can be defined using the <b>var</b> or <b>let</b> keywords.", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Build PDF
    doc.build(story)
    print(f"Test PDF created: {output_path}")


def test_translation(model_path="/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf"):
    """Test the translation with formatting preservation."""
    # Create test input PDF
    input_pdf = "test_input.pdf"
    output_pdf = "test_output_italian.pdf"
    
    create_test_pdf(input_pdf)
    
    # Initialize translator
    print("\n" + "="*60)
    print("Initializing translator...")
    translator = PDFTranslator(model_path=model_path)
    
    # Perform translation
    print("="*60)
    success = translator.translate_pdf(input_pdf, output_pdf)
    
    if success:
        print("\n" + "="*60)
        print("✅ Translation test completed successfully!")
        print(f"Input file: {input_pdf}")
        print(f"Output file: {output_pdf}")
        print("\nPlease open both PDFs to verify:")
        print("1. Bold text is still bold")
        print("2. Italic text is still italic")
        print("3. Red text is still red")
        print("4. Green text is still green")
        print("5. Line breaks are in the same positions")
        print("="*60)
    else:
        print("\n❌ Translation test failed!")
        print("Check the error messages above for details.")


def quick_test():
    """Quick test without creating input PDF (use existing PDF)."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_formatting.py <input_pdf>")
        print("Or run without arguments to create and test a sample PDF")
        return
    
    input_pdf = sys.argv[1]
    output_pdf = input_pdf.replace('.pdf', '_italian.pdf')
    
    if not os.path.exists(input_pdf):
        print(f"Error: File not found: {input_pdf}")
        return
    
    translator = PDFTranslator(model_path="/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf")
    success = translator.translate_pdf(input_pdf, output_pdf)
    
    if success:
        print(f"\n✅ Translation completed: {output_pdf}")
    else:
        print("\n❌ Translation failed!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test with provided PDF
        quick_test()
    else:
        # Create test PDF and translate
        test_translation()
