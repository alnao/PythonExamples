"""
PDF Translator using Llama Model or GitHub Copilot CLI
This module provides a class to translate PDF documents from English to Italian
using either a local Llama model or GitHub Copilot CLI, preserving formatting (bold, italic, colors, line breaks).
"""

import os
import subprocess
from typing import List, Optional, Dict, Tuple
import requests
import pymupdf # fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import HexColor, black
from llama_cpp import Llama


class PDFTranslator:
    CHUNK_BLOCK_SIZE=10  # Number of text blocks to group together for translation
    FROM_LIST_NOTE=" Text it's a block from a list of blocks, separated by 3 new line in the prompt. Preserve this structure in the translation."    
    SEPARATOR=" \n\n\n "  # Separator used to join multiple blocks for translation while preserving structure
    LIST_MODE=False;
    """
    A class to handle PDF translation from English to Italian using Llama model or GitHub Copilot CLI.
    """
    
    def __init__(self, model_path: str = None, n_ctx: int = 2048, n_threads: int = 4, 
                 translation_engine: str = "llama", copilot_model: str = "gpt-5", libretranslate_url: str = "http://localhost:5000/translate"):
        """
        Initialize the PDF Translator.
        
        Args:
            model_path: Path to the Llama model file (.gguf) - required for 'llama' engine
            n_ctx: Context window size (default: 2048) - for Llama
            n_threads: Number of threads for processing (default: 4) - for Llama
            translation_engine: Translation engine to use: 'llama' or 'copilot' (default: 'llama')
            copilot_model: Model to use with Copilot CLI: 'gpt-5', 'claude-sonnet-4.5', 'gpt-5-mini' (default: 'gpt-5')
        """
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.translation_engine = translation_engine.lower()
        self.copilot_model = copilot_model
        self.libretranslate_url = libretranslate_url
        self.llm = None
        
        if self.translation_engine == "llama":
            self._load_model()
        elif self.translation_engine == "copilot":
            self._check_copilot_cli()
        elif self.translation_engine == "libre":
            # No heavy init; assume LibreTranslate service is reachable
            print(f"LibreTranslate endpoint set to {self.libretranslate_url}")
        else:
            raise ValueError(f"Unknown translation engine: {translation_engine}. Use 'llama', 'copilot', or 'libre'.")
    
    def _load_model(self):
        """Load the Llama model."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        print(f"Loading Llama model from {self.model_path}...")
        """
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_threads=self.n_threads,
            verbose=False
        )
        """
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_threads=self.n_threads,   # set to os.cpu_count()
            n_batch=256,                # larger batch
            n_gpu_layers=0,            # >0 if GPU available, else 0
            verbose=False
        )
        print("Model loaded successfully!")
    
    def _check_copilot_cli(self):
        """Check if GitHub Copilot CLI is available."""
        try:
            result = subprocess.run(
                ["copilot", "--version"],#ex "gh"
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("GitHub Copilot CLI is available!")
            else:
                raise RuntimeError("GitHub Copilot CLI is not properly configured.")
        except FileNotFoundError:
            raise RuntimeError("GitHub CLI (gh) is not installed. Please install it first.")
        except subprocess.TimeoutExpired:
            raise RuntimeError("GitHub Copilot CLI check timed out.")
        except Exception as e:
            raise RuntimeError(f"Error checking GitHub Copilot CLI: {e}")
    
    def extract_text_from_pdf(self, pdf_path: str, two_columns: bool = False) -> List[Dict]:
        """
        Extract text from PDF file page by page with formatting information.

        Args:
            pdf_path: Path to the PDF file
            two_columns: When True, order text assuming a two-column layout (left column first)

        Returns:
            List of dictionaries, each containing formatted text blocks from one page
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        doc = pymupdf.open(pdf_path)
        pages_data = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text with formatting details
            blocks = []
            text_dict = page.get_text("dict")
            page_width = page.rect.width
            
            for block in text_dict["blocks"]:
                if "lines" in block:  # Text block
                    for line in block["lines"]:
                        line_text = ""
                        line_format = []
                        
                        for span in line["spans"]:
                            text = span["text"]
                            if text.strip():
                                # Extract formatting information
                                font_name = span["font"]
                                font_size = span["size"]
                                color = span["color"]
                                flags = span["flags"]
                                
                                # Determine formatting flags
                                is_bold = flags & 2**4 or "bold" in font_name.lower()
                                is_italic = flags & 2**1 or "italic" in font_name.lower()
                                
                                # Convert color integer to hex
                                if color:
                                    color_hex = "#{:06x}".format(color)
                                else:
                                    color_hex = "#000000"
                                
                                line_format.append({
                                    "text": text,
                                    "bold": is_bold,
                                    "italic": is_italic,
                                    "color": color_hex,
                                    "size": round(font_size)
                                })
                                line_text += text
                        
                        if line_text.strip():
                            blocks.append({
                                "text": line_text,
                                "format": line_format,
                                "y_position": line["bbox"][1],
                                "x_position": line["bbox"][0]
                            })

            # Sort blocks respecting the chosen layout
            if two_columns and blocks:
                mid_x = page_width / 2
                left = [b for b in blocks if b["x_position"] <= mid_x]
                right = [b for b in blocks if b["x_position"] > mid_x]
                left.sort(key=lambda b: (b["y_position"], b["x_position"]))
                right.sort(key=lambda b: (b["y_position"], b["x_position"]))
                blocks = left + right
            else:
                blocks.sort(key=lambda b: (b["y_position"], b["x_position"]))

            def _format_signature(fmt: List[Dict]) -> Tuple:
                if not fmt:
                    return (False, False, "#000000", None)
                first = (
                    fmt[0].get("bold", False),
                    fmt[0].get("italic", False),
                    fmt[0].get("color", "#000000"),
                    fmt[0].get("size", None),
                )
                if all(
                    (
                        span.get("bold", False),
                        span.get("italic", False),
                        span.get("color", "#000000"),
                        span.get("size", None),
                    )
                    == first
                    for span in fmt
                ):
                    return ("uniform",) + first
                return ("mixed", tuple(
                    (
                        span.get("bold", False),
                        span.get("italic", False),
                        span.get("color", "#000000"),
                        span.get("size", None),
                    )
                    for span in fmt
                ))

            def compare_signature(sig1: Optional[Tuple], sig2: Optional[Tuple]) -> bool:
                """Return True when format signatures are equivalent within a size delta of 1 point."""
                if not sig1 or not sig2:
                    return False
                if sig1[0] != sig2[0]:
                    return False

                def _size_close(a: Optional[float], b: Optional[float]) -> bool:
                    if a is None or b is None:
                        return a == b
                    return abs(a - b) <= 1

                # Uniform signatures: ("uniform", bold, italic, color, size)
                if sig1[0] == "uniform":
                    _, b1, i1, c1, s1 = sig1
                    _, b2, i2, c2, s2 = sig2
                    return b1 == b2 and i1 == i2 and c1 == c2 and _size_close(s1, s2)

                # Mixed signatures: ("mixed", ((b,i,c,s), ...))
                if len(sig1) != len(sig2):
                    return False
                spans1 = sig1[1]
                spans2 = sig2[1]
                if len(spans1) != len(spans2):
                    return False
                for (b1, i1, c1, s1), (b2, i2, c2, s2) in zip(spans1, spans2):
                    if b1 != b2 or i1 != i2 or c1 != c2 or not _size_close(s1, s2):
                        return False
                return True


            # Aggregate consecutive blocks sharing the same formatting signature
            aggregated: List[Dict] = []
            current_sig: Optional[Tuple] = None

            for block in blocks:
                sig = _format_signature(block.get("format", []))
                if aggregated and compare_signature(sig, current_sig):
                    # Merge text with a newline separator to preserve line boundaries
                    aggregated[-1]["text"] = f"{aggregated[-1]['text']}\n{block['text']}"
                else:
                    aggregated.append(block)
                    current_sig = sig

            blocks = aggregated

            if blocks:
                pages_data.append({"page_num": page_num + 1, "blocks": blocks})
                print(f"Extracted {len(blocks)} text blocks from page {page_num + 1}")
            else:
                print(f"Warning: Page {page_num + 1} is empty or has no extractable text")
        
        doc.close()
        return pages_data
    
    def translate_text_list(self, text_list: List[str], max_length: int = 1500, format_info: Optional[List[Dict]] = None) -> str:
        """
        Translate text from English to Italian using the configured engine.

        Args a list of blocks with text and formatting info, preserving line breaks and formatting:
            text: English text to translate
            max_length: Kept for API compatibility (no chunking performed)
            format_info: Formatting info (unused here, preserved for signature compatibility)

        Returns:
            Translated Italian text
        """
        result = []
        # separa la text_list in sottoliste da 10 elementi ciascuna
        for i in range(0, len(text_list), self.CHUNK_BLOCK_SIZE):
            sublist = text_list[i:i+10]
            # per ogni sottolista, unisce i testi in 
            text_to_traslate = self.SEPARATOR.join(sublist)            
            # li traduce insieme, preservando la struttura
            sub_result = self._translate_chunk(text_to_traslate, True)
            # per ogni risulato, lo divide di nuovo in sottolista usando SEPARATOR e lo aggiunge alla lista finale dei risultati
            result.extend(sub_result.split(self.SEPARATOR))
        
        return result

    def translate_text(self, text: str, max_length: int = 1500, format_info: Optional[List[Dict]] = None) -> str:
        """
        Translate text from English to Italian using the configured engine.

        Args :
            text: English text to translate
            max_length: Kept for API compatibility (no chunking performed)
            format_info: Formatting info (unused here, preserved for signature compatibility)

        Returns:
            Translated Italian text
        """
        if not text.strip():
            return ""

        return self._translate_chunk(text)
    
    
    def _translate_chunk(self, text: str, from_list: bool = False) -> str:
        """
        Translate a single chunk of text, preserving line breaks.
        
        Args:
            text: English text chunk to translate
            
        Returns:
            Translated Italian text
        """
        if self.translation_engine == "llama":
            return self._translate_with_llama(text,from_list)
        elif self.translation_engine == "copilot":
            return self._translate_with_copilot(text,from_list)
        elif self.translation_engine == "libre":
            return self._translate_with_libretranslate(text, from_list)
        else:
            return text
    
    def _translate_with_llama(self, text: str, from_list: bool = False) -> str:
        """
        Translate text using Llama model.
        
        Args:
            text: English text to translate
            
        Returns:
            Translated Italian text
        """
        prompt = f"""You are a professional translator. Translate the following English text to Italian. 
IMPORTANT: Preserve all line breaks exactly as they appear in the original text. Keep the technical terms accurate and maintain the original formatting structure.
Only provide the translation, no explanations.
{self.FROM_LIST_NOTE if from_list else ""}

English text:
{text}"""
        #print(prompt)
        print (f"- Translating chunk (length {len(text)}): {text.replace("\n\n\n","\n- - ")[:60]}{'...' if len(text) > 60 else ''}")

        try:
            response = self.llm(
                prompt,
                max_tokens=2048,
                temperature=0.3,
                top_p=0.9,
                echo=False,
                stop=["English text:", "Translate"]
            )
            
            translated_text = response['choices'][0]['text'].strip()
            return translated_text
        except Exception as e:
            print(f"Translation error: {e}")
            return text  # Return original text if translation fails
    
    def _translate_with_copilot(self, text: str, from_list: bool = False) -> str:
        """
        Translate text using GitHub Copilot CLI.
        
        Args:
            text: English text to translate
            
        Returns:
            Translated Italian text
        """
        prompt = f"""Translate the following English text to Italian. 
IMPORTANT: Preserve all line breaks exactly as they appear in the original text. 
{self.FROM_LIST_NOTE if from_list else ""}
Keep technical terms accurate and maintain the original formatting structure.
Only provide the Italian translation, no explanations or additional text.

English text:
{text}"""
        print (f"- Translating chunk (length {len(text)}): {text.replace("\n\n\n","\n- - ")[:60]}{'...' if len(text) > 60 else ''}")
        try:
            # Build command with model selection
            command = ["copilot"] # ["gh","copilot", "suggest", "-t", "shell"]
            
            # Add model parameter if specified
            if self.copilot_model:
                command.extend(["--model", self.copilot_model])
            command.extend(["--prompt", prompt])
            # Use gh copilot suggest command
# DEBUG
#            print("    ", command)
            result = subprocess.run(
                command,
                # ex                input=prompt,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # Parse the output to get just the translation
                output = result.stdout.strip()
                # Remove any command suggestions or extra formatting
                lines = output.split('\n')
                # Filter out lines that look like shell commands or explanations
                translation_lines = [line for line in lines if line.strip() and not line.startswith('$') and not line.startswith('#')]
                translated_text = '\n'.join(translation_lines)
                return translated_text if translated_text else text
            else:
                print(f"Copilot CLI error: {result.stderr}")
                return text
                
        except subprocess.TimeoutExpired:
            print("Copilot CLI timeout - request took too long")
            return text
        except Exception as e:
            print(f"Translation error with Copilot: {e}")
            return text

    def _translate_with_libretranslate(self, text: str, from_list: bool = False) -> str:
        """Translate text using a local LibreTranslate server."""
        payload = {
            "q": text,
            "source": "en",
            "target": "it",
            "format": "text"
        }

        try:
            print (f"- Translating chunk (length {len(text)}): {text.replace('\n\n\n','\n- - ')[:60]}{'...' if len(text) > 60 else ''}")
            resp = requests.post(self.libretranslate_url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "translatedText" in data:
                return data["translatedText"]
            # Some deployments return list
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict) and "translatedText" in first:
                    return first["translatedText"]
            return text
        except Exception as e:
            print(f"Translation error with LibreTranslate: {e}")
            return text
    
    def translate_pages(self, pages_data: List[Dict]) -> List[Dict]:
        """
        Translate multiple pages with formatting preservation.
        
        Args:
            pages_data: List of page data with formatting information
            
        Returns:
            List of translated page data with preserved formatting
        """
        translated_pages = []
        if self.LIST_MODE: #prova list mode che poi non funziona!
            for page_data in pages_data:
                page_num = page_data["page_num"]
                blocks = page_data["blocks"]
                
                print(f"\nTranslating page {page_num}/{len(pages_data)} with LIST_MODE [DOESN'T WORK YET]...")
#TODO: check why LIST_MODE doesn't work
                to_traslate = [block["text"].replace("-\n", "").replace("\n", "")  for block in blocks]
                #to_traslate = [f"{i}: {block['text']}" for i, block in enumerate(blocks)]
                translated_texts = self.translate_text_list(to_traslate)
                
                translated_blocks=[]
                for i, block in enumerate(blocks):
                    original_text = block["text"]
                    format_info = block["format"]
                    traslated_text = translated_texts[i] if i < len(translated_texts) else original_text  # Fallback to original if translation missing
                    if i < len(translated_texts):
                        print (f"    Original text (length {len(original_text)}): {original_text[:60]}{'...' if len(original_text) > 60 else ''}")
                        print (f"    Translated text (length {len(translated_texts[i])}): {translated_texts[i][:60]}{'...' if len(translated_texts[i]) > 60 else ''}")
                    translated_blocks.append({
                        "text": traslated_text,
                        "format": format_info,  # Keep original formatting
                        "original_text": original_text
                    })            
                translated_pages.append({
                    "page_num": page_num,
                    "blocks": translated_blocks
                })
        else:
            for page_data in pages_data:
                page_num = page_data["page_num"]
                blocks = page_data["blocks"]
                translated_blocks=[]
                print(f"\nTranslating page {page_num}/{len(pages_data)} with UNIQUE MODE ...")

                for block in blocks:
                    original_text = block["text"]
                    format_info = block["format"]
                    
                    #print (f"    Original text (length {len(original_text)}): {original_text[:60]}{'...' if len(original_text) > 60 else ''}")
                    # Translate the text (format-aware chunking)
                    translated_text = self.translate_text(original_text, format_info=format_info)
                    
                    # Preserve formatting by mapping it to translated text
                    translated_blocks.append({
                        "text": translated_text,
                        "format": format_info,  # Keep original formatting
                        "original_text": original_text
                    })
                translated_pages.append({
                    "page_num": page_num,
                    "blocks": translated_blocks
                })
        
        return translated_pages
    
    def _apply_formatting_to_text(self, text: str, format_info: List[Dict]) -> str:
        """
        Apply ReportLab XML-like formatting tags to text based on format info.
        
        Args:
            text: Plain text
            format_info: List of formatting dictionaries
            
        Returns:
            Text with ReportLab formatting tags
        """
        if not format_info:
            return text
        
        # Use the dominant formatting from the first segment
        first_format = format_info[0]
        is_bold = first_format.get("bold", False)
        is_italic = first_format.get("italic", False)
        color = first_format.get("color", "#000000")
        
        # Build formatted text
        formatted = text
        
        # Apply bold
        if is_bold:
            formatted = f"<b>{formatted}</b>"
        
        # Apply italic
        if is_italic:
            formatted = f"<i>{formatted}</i>"
        
        # Apply color if not black
        if color and color != "#000000":
            formatted = f'<font color="{color}">{formatted}</font>'
        
        return formatted
    
    def create_pdf(self, translated_pages: List[Dict], output_path: str):
        """
        Create a PDF file from translated text with formatting preservation.
        
        Args:
            translated_pages: List of translated page data with formatting
            output_path: Path where the PDF will be saved
        """
        # Additionally, emit a CSV alongside the PDF with original/translated text and formatting
        csv_path = f"{os.path.splitext(output_path)[0]}.csv"
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Container for the 'Flowable' objects
        elements = []

        # Collect rows for CSV: page, block_index, original, translated, format
        csv_rows = []
        
        # Define styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=styles['BodyText'],
            alignment=TA_LEFT,
            fontSize=11,
            leading=14,
            spaceAfter=6
        ))
        
        # Add content with formatting
        for page_data in translated_pages:
            blocks = page_data["blocks"]
            
            for block in blocks:
                translated_text = block["text"]
                format_info = block["format"]
                original_text = block.get("original_text", "")
                
                if translated_text.strip():
                    # Apply formatting to the text
                    formatted_text = self._apply_formatting_to_text(translated_text, format_info)
                    
                    # Create paragraph with formatting
                    try:
                        para = Paragraph(formatted_text, styles['CustomNormal'])
                        elements.append(para)
                        # Small spacer after each block (line)
                        elements.append(Spacer(1, 0.05 * inch))
                    except Exception as e:
                        # Fallback to plain text if formatting fails
                        print(f"Warning: Formatting error, using plain text: {e}")
                        para = Paragraph(translated_text, styles['CustomNormal'])
                        elements.append(para)
                        elements.append(Spacer(1, 0.05 * inch))

                csv_rows.append({
                    "page": page_data["page_num"],
                    "block_index": len(csv_rows) + 1,
                    "original": original_text,
                    "translated": translated_text,
                    "format": format_info
                })
            
            # Add page break except for the last page
            if page_data != translated_pages[-1]:
                elements.append(PageBreak())
        
        # Build PDF
        try:
            doc.build(elements)
            print(f"\nPDF created successfully: {output_path}")
            # Write CSV summary
            try:
                import csv
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["page", "block_index", "original", "translated", "format"])
                    for row in csv_rows:
                        writer.writerow([
                            row["page"],
                            row["block_index"],
                            row["original"],
                            row["translated"],
                            row["format"],
                        ])
                print(f"CSV created successfully: {csv_path}")
            except Exception as e:
                print(f"Error writing CSV summary: {e}")
        except Exception as e:
            print(f"Error building PDF: {e}")
            # Try again with simpler formatting
            print("Attempting to create PDF without complex formatting...")
            self._create_simple_pdf(translated_pages, output_path)
    
    def _create_simple_pdf(self, translated_pages: List[Dict], output_path: str):
        """
        Fallback method to create PDF with minimal formatting if complex formatting fails.
        
        Args:
            translated_pages: List of translated page data
            output_path: Path where the PDF will be saved
        """
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        for page_data in translated_pages:
            for block in page_data["blocks"]:
                text = block["text"]
                if text.strip():
                    para = Paragraph(text, styles['BodyText'])
                    elements.append(para)
                    elements.append(Spacer(1, 0.1 * inch))
            
            if page_data != translated_pages[-1]:
                elements.append(PageBreak())
        
        doc.build(elements)
        print(f"PDF created with simplified formatting: {output_path}")
    
    def translate_pdf(self, input_pdf_path: str, output_pdf_path: str, two_columns: bool = False) -> bool:
        """
        Complete workflow: Extract text from PDF with formatting, translate it, and create a new PDF.

        Args:
            input_pdf_path: Path to the input English PDF
            output_pdf_path: Path for the output Italian PDF
            two_columns: When True, treat the source PDF as two-column layout

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"\nStarting translation process...")
            print(f"Input: {input_pdf_path}")
            print(f"Output: {output_pdf_path}")
            
            # Extract text from PDF with formatting
            print("\n[1/3] Extracting text with formatting from PDF...")
            pages_data = self.extract_text_from_pdf(input_pdf_path, two_columns=two_columns)
            
            if not pages_data:
                print("Error: No text could be extracted from the PDF")
                return False
            
            print(f"Successfully extracted formatted text from {len(pages_data)} pages")
            
            # Translate pages with formatting preservation
            print("\n[2/3] Translating text while preserving formatting...")
            translated_pages = self.translate_pages(pages_data)
            
            # Create new PDF with formatting
            print("\n[3/3] Creating translated PDF with formatting...")
            self.create_pdf(translated_pages, output_pdf_path)
            
            print("\n" + "="*50)
            print("Translation completed successfully!")
            print("="*50)
            return True
            
        except Exception as e:
            print(f"\nError during translation: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    # Example usage
    MODEL_PATH = "/mnt/Virtuali/mistral-7b-instruct-v0.2.Q2_K.gguf" # "/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf"
    
    translator = PDFTranslator(model_path=MODEL_PATH)
    
    # Test translation
    input_pdf = "input.pdf"
    output_pdf = "output_italian.pdf"
    
    if os.path.exists(input_pdf):
        translator.translate_pdf(input_pdf, output_pdf)
    else:
        print(f"Test file '{input_pdf}' not found. Please provide a PDF file to translate.")
