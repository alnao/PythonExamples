# Multi-Engine Translation Support

## Overview

The PDF Translator now supports two translation engines:

1. **Llama 2** - Local AI model (privacy-focused, no internet required)
2. **GitHub Copilot CLI** - Cloud-based translation (requires GitHub CLI and authentication)

## Features

### Translation Engine Selection
- Users can choose their preferred translation engine from the web interface
- Visual status indicators show which engines are available
- Radio button selector for easy engine switching
- Each engine has specific requirements and advantages

### Llama 2 Engine
**Advantages:**
- 100% local processing - documents never leave your machine
- No internet connection required
- Complete privacy and data security
- Works with the existing model file

**Requirements:**
- Llama 2 model file (.gguf format)
- Model path: `/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf`
- At least 8GB RAM (16GB recommended)
- `llama-cpp-python` package installed

### GitHub Copilot CLI Engine
**Advantages:**
- Uses OpenAI's GPT-4 model (potentially better quality)
- No local model file required
- Less RAM usage
- Can handle complex translations

**Requirements:**
- GitHub CLI (`gh`) installed
- GitHub Copilot CLI extension installed
- Active GitHub Copilot subscription
- Internet connection
- Authenticated GitHub account

## Installation

### Installing GitHub CLI (for Copilot support)

**Ubuntu/Debian:**
```bash
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

**macOS:**
```bash
brew install gh
```

**Windows:**
```bash
winget install --id GitHub.cli
```

### Setting up GitHub Copilot CLI

1. **Authenticate with GitHub:**
   ```bash
   gh auth login
   ```

2. **Install Copilot CLI extension:**
   ```bash
   gh extension install github/gh-copilot
   ```

3. **Verify installation:**
   ```bash
   gh copilot --version
   ```

## Usage

### Web Interface

1. **Start the application:**
   ```bash
   cd /mnt/Dati4/Workspace/PythonExamples/IA/llama_pdf_traslator
   python3 app.py
   ```

2. **Access the web interface:**
   Open your browser to: `http://localhost:5000`

3. **Check engine availability:**
   - Green badges indicate available engines
   - Gray badges indicate unavailable engines

4. **Upload and translate:**
   - Upload your PDF file
   - Select translation engine (Llama or Copilot)
   - Click "Translate to Italian"
   - Wait for processing
   - Download translated PDF

### Programmatic Usage

```python
from translator import PDFTranslator

# Using Llama engine
llama_translator = PDFTranslator(
    model_path="/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf",
    translation_engine="llama"
)
llama_translator.translate_pdf("input.pdf", "output_llama.pdf")

# Using Copilot engine
copilot_translator = PDFTranslator(
    translation_engine="copilot"
)
copilot_translator.translate_pdf("input.pdf", "output_copilot.pdf")
```

## Architecture

### Backend Changes

**translator.py:**
- Added `translation_engine` parameter to `__init__`
- Added `_check_copilot_cli()` method to verify Copilot availability
- Split `_translate_chunk()` into two methods:
  - `_translate_with_llama()` - Uses local Llama model
  - `_translate_with_copilot()` - Uses GitHub Copilot CLI via subprocess

**app.py:**
- Changed from single `translator` to `llama_translator` and `copilot_translator`
- Added `get_translator(engine)` function to return appropriate translator
- Modified `translate_in_background()` to accept engine parameter
- Updated `/upload` route to accept engine selection from form
- Modified health check to show both engine statuses
- Updated initialization to attempt loading both engines

### Frontend Changes

**index.html:**
- Added engine status indicators at top (Llama & Copilot)
- Added radio button selector for engine choice
- Updated features section to mention multi-engine support
- Modified footer text
- Added helpful tooltips explaining each engine

**status.html:**
- Added engine badge in job information section
- Updated "What's happening" message to be dynamic based on engine
- Shows which engine is processing the translation

## Technical Details

### GitHub Copilot CLI Integration

The Copilot integration uses subprocess to call `gh copilot suggest`:

```python
result = subprocess.run(
    ["gh", "copilot", "suggest", "-t", "shell"],
    input=prompt,
    capture_output=True,
    text=True,
    timeout=60
)
```

**Prompt Format:**
```
Translate the following English text to Italian. 
IMPORTANT: Preserve all line breaks exactly as they appear in the original text. 
Keep technical terms accurate and maintain the original formatting structure.
Only provide the Italian translation, no explanations or additional text.

{text to translate}
```

**Output Parsing:**
The Copilot CLI output is parsed to extract just the translation, filtering out:
- Shell command suggestions (lines starting with `$`)
- Comments (lines starting with `#`)
- Extra whitespace

### Error Handling

Both engines have fallback mechanisms:
- If translation fails, returns original text
- Timeout handling (60 seconds for Copilot)
- Engine availability checks before processing
- Graceful degradation if one engine isn't available

## Troubleshooting

### Copilot Issues

**Problem:** "GitHub CLI (gh) is not installed"
**Solution:** Install GitHub CLI following the installation instructions above

**Problem:** "GitHub Copilot CLI is not properly configured"
**Solution:** 
```bash
gh auth login
gh extension install github/gh-copilot
gh copilot --version
```

**Problem:** Copilot translations are slow
**Solution:** This is normal - Copilot makes API calls to GitHub servers. Local Llama is faster.

**Problem:** Copilot returns empty translations
**Solution:** Check your Copilot subscription status and internet connection

### Llama Issues

**Problem:** "Model file not found"
**Solution:** Verify model path in `app.py` and ensure file exists

**Problem:** Out of memory errors
**Solution:** Switch to Copilot engine which uses less RAM

## Performance Comparison

| Feature | Llama 2 | GitHub Copilot CLI |
|---------|---------|-------------------|
| Speed | Fast (local) | Slower (API calls) |
| Privacy | 100% private | Data sent to GitHub |
| Internet | Not required | Required |
| RAM Usage | 8-16GB | <2GB |
| Quality | Good | Excellent |
| Cost | Free (after model) | Requires subscription |

## Configuration

### Changing Default Engine

Edit `app.py`:
```python
# Set default engine in upload form
engine = request.form.get('engine', 'copilot')  # Default to Copilot
```

### Adjusting Timeouts

For Copilot CLI in `translator.py`:
```python
result = subprocess.run(
    ["gh", "copilot", "suggest", "-t", "shell"],
    input=prompt,
    capture_output=True,
    text=True,
    timeout=120  # Increase to 120 seconds
)
```

## Future Enhancements

Potential improvements:
- [ ] Add more engines (OpenAI API, Claude, etc.)
- [ ] Engine performance metrics
- [ ] Cost tracking for cloud-based engines
- [ ] Automatic engine selection based on document complexity
- [ ] Batch translation with mixed engines
- [ ] Engine-specific quality settings

## API Reference

### PDFTranslator Class

```python
PDFTranslator(
    model_path: str = None,
    n_ctx: int = 2048,
    n_threads: int = 4,
    translation_engine: str = "llama"
)
```

**Parameters:**
- `model_path`: Path to Llama model file (required for 'llama' engine)
- `n_ctx`: Context window size for Llama
- `n_threads`: Number of CPU threads for Llama
- `translation_engine`: Engine to use ('llama' or 'copilot')

**Methods:**
- `translate_pdf(input_path, output_path)`: Translate entire PDF
- `translate_text(text)`: Translate text string
- `extract_text_from_pdf(pdf_path)`: Extract formatted text from PDF

## License

All engine integrations respect the original licenses:
- Llama 2: Meta's Llama 2 license
- GitHub Copilot: GitHub Terms of Service

---

**Note:** Always respect licensing terms and usage policies for both Llama 2 and GitHub Copilot when using this tool.
