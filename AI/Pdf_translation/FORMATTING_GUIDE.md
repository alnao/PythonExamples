# Formatting Preservation Guide

## Overview

The PDF translator now preserves formatting from the original PDF document in the translated output. This includes:

- ✅ **Bold text**
- ✅ **Italic text**
- ✅ **Text colors** (red, blue, etc.)
- ✅ **Line breaks** (preserved in exact positions)
- ✅ **Reading order** (maintained based on vertical position)

## How It Works

### 1. Text Extraction with PyMuPDF

The translator uses PyMuPDF (fitz) instead of PyPDF to extract text with formatting:

```python
# Each text span contains:
{
    "text": "Hello World",
    "font": "Arial-Bold",
    "size": 12,
    "color": 16711680,  # Red in integer format
    "flags": 20  # Font flags (bold, italic, etc.)
}
```

### 2. Format Detection

**Bold Detection:**
- Font flags bit 4 is set, OR
- Font name contains "bold" (case-insensitive)

**Italic Detection:**
- Font flags bit 1 is set, OR
- Font name contains "italic" (case-insensitive)

**Color Detection:**
- Color integer is converted to hex format (#RRGGBB)
- Example: `16711680` → `#FF0000` (red)

### 3. Format Preservation

Formatting is maintained throughout translation:

1. **Extract**: Text blocks are extracted with format metadata
2. **Translate**: Plain text is translated while format info is preserved
3. **Apply**: ReportLab XML tags are added to translated text:
   - Bold: `<b>text</b>`
   - Italic: `<i>text</i>`
   - Color: `<font color="#FF0000">text</font>`

### 4. Line Break Preservation

Line breaks are preserved by:
- Extracting text line-by-line instead of as continuous blocks
- Splitting translation chunks at line boundaries
- Instructing the AI model to maintain line breaks
- Creating separate Paragraph objects for each line in output

## Example

**Original PDF:**
```
This is normal text.
This is bold text.
This is italic text.
This is red text.
```

**Translated PDF (Italian):**
```
Questo è testo normale.
Questo è testo in grassetto.
Questo è testo in corsivo.
Questo è testo rosso.
```

All formatting (bold, italic, red color) and line breaks are preserved!

## Supported Formatting

| Feature | Supported | Notes |
|---------|-----------|-------|
| Bold | ✅ | Detected via font flags and names |
| Italic | ✅ | Detected via font flags and names |
| Colors | ✅ | All colors preserved as hex |
| Line Breaks | ✅ | Exact position preserved |
| Font Size | ⚠️ | Detected but not yet applied |
| Underline | ❌ | Not yet supported |
| Strikethrough | ❌ | Not yet supported |
| Subscript/Superscript | ❌ | Not yet supported |

## Fallback Mechanism

If complex formatting causes PDF generation to fail, the system automatically falls back to simplified formatting:

1. Attempts to create PDF with full formatting
2. If error occurs, catches exception
3. Recreates PDF with plain text only
4. Ensures translation always completes successfully

## Testing Formatting Preservation

To test if formatting is preserved:

1. Create a test PDF with:
   - Some **bold text**
   - Some *italic text*
   - Some <span style="color:red">red text</span>
   - Multiple line breaks

2. Upload the PDF through the web interface

3. Download the translated PDF

4. Verify:
   - Bold sections remain bold
   - Italic sections remain italic
   - Red text remains red
   - Line breaks appear in same positions

## Troubleshooting

### Formatting Not Preserved

**Problem**: Output PDF has no formatting

**Solution**:
- Check that PyMuPDF is installed: `pip install PyMuPDF==1.23.8`
- Verify input PDF has actual formatting (not just styled appearance)
- Check console output for formatting extraction messages

### Colors Look Wrong

**Problem**: Colors are different in output

**Solution**:
- Some PDFs use color profiles that may differ
- Colors are converted directly from source values
- Check if original PDF uses RGB vs CMYK colors

### Line Breaks Missing

**Problem**: Output PDF has different line breaks

**Solution**:
- Update the translation prompt to emphasize line break preservation
- Reduce chunk size in `translate_text()` method
- Check if Llama model is following line break instructions

### PDF Generation Fails

**Problem**: Error when creating output PDF

**Solution**:
- Check ReportLab installation: `pip install reportlab==4.0.7`
- System will automatically try simplified formatting
- Check for special characters that need escaping

## Configuration Options

### Adjust Format Detection Sensitivity

In `translator.py`, modify the format detection:

```python
# Make bold detection more sensitive
is_bold = (flags & 2**4) or ("bold" in font_name.lower()) or (font_weight > 500)

# Make italic detection more sensitive  
is_italic = (flags & 2**1) or ("italic" in font_name.lower()) or ("oblique" in font_name.lower())
```

### Adjust Chunk Size for Better Line Break Preservation

```python
# In translate_text() method
def translate_text(self, text: str, max_length: int = 1000):  # Reduced from 1500
    # Smaller chunks = better line break preservation
```

### Customize Output Styling

```python
# In create_pdf() method
styles.add(ParagraphStyle(
    name='CustomNormal',
    fontSize=11,        # Adjust font size
    leading=14,         # Adjust line spacing
    spaceAfter=6       # Adjust space between lines
))
```

## Future Enhancements

Planned improvements:
- [ ] Font size preservation
- [ ] Underline support
- [ ] Strikethrough support
- [ ] Better color profile handling
- [ ] Table formatting preservation
- [ ] Image position preservation
- [ ] Hyperlink preservation

## Dependencies

Make sure these packages are installed:

```bash
pip install PyMuPDF==1.23.8    # For format extraction
pip install reportlab==4.0.7    # For formatted PDF generation
```

## API Usage

```python
from translator import PDFTranslator

# Initialize translator
translator = PDFTranslator(
    model_path="/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf"
)

# Translate with formatting preservation
translator.translate_pdf(
    input_pdf_path="document.pdf",
    output_pdf_path="document_italian.pdf"
)
```

The formatting is automatically preserved - no additional configuration needed!

---

**Note**: Formatting preservation works best with PDFs that have actual text with formatting tags. Scanned PDFs or images will not preserve formatting as they require OCR first.
