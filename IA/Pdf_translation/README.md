# PDF Translator - English to Italian

**Made with ❤️ for local, private PDF translation**

A web-based PDF translation application that translates documents from English to Italian using
- local Llama 2 model
- GitHub Copilot CLI 
- LibreTranslate server
The application provides a user-friendly interface built with Flask and Bootstrap 5, allowing users to upload PDF files and download translated versions.

## 🌟 Features

- **Multi-Engine Support**: Choose between Llama 2 (local) or GitHub Copilot CLI (cloud)
- **Local AI Translation**: Uses Llama 2 model running locally for privacy and security
- **Cloud Translation**: Optional GitHub Copilot CLI integration for high-quality translations
- **Lightweight REST Translation**: Optional LibreTranslate engine via local Docker container
- **Formatting Preservation**: Maintains bold, italic, colors, and line breaks from original PDF
- **PDF to PDF**: Direct PDF input and output - no intermediate formats
- **Line Break Preservation**: Keeps all line breaks in the same positions as the original
- **Web Interface**: Beautiful, responsive UI built with Bootstrap 5
- **Real-time Status**: Live translation progress tracking
- **Drag & Drop**: Easy file upload with drag-and-drop support
- **Privacy Options**: Choose local processing (Llama) or cloud processing (Copilot)
- **Technical Accuracy**: Optimized for technical and formal document translation

## 📋 Prerequisites

### For Llama Engine:
- Python 3.8 or higher
- Llama 2 model file (GGUF format)
- At least 8GB RAM (16GB recommended)
- Linux, macOS, or Windows with WSL

### For Copilot Engine:
- Python 3.8 or higher
- GitHub CLI (`gh`) installed
- GitHub Copilot subscription
- Internet connection
- Authenticated GitHub account

### For LibreTranslate
- Python 3.8
- LibreTranslate server, it's succested run LibreTranslate server on docker image server, for example run it with:
      ```bash
      docker run -ti --rm -p 5001:5000 libretranslate/libretranslate --load-only en,it
      ```


### For LibreTranslate Engine:
- Docker installed and running
- Pull and start the container (English↔Italian only to save memory):
   ```bash
   docker run -ti --rm -p 5001:5000 libretranslate/libretranslate --load-only en,it
   ```
- Endpoint (default): `http://localhost:5001/translate` — change with `LIBRETRANSLATE_URL` if needed

## 📁 Project Structure

```
llama_pdf_traslator/
├── app.py                 # Flask web application
├── translator.py          # PDF translation class (multi-engine)
├── requirements.txt       # Python dependencies
├── README.md              # Main documentation
├── MULTI_ENGINE_GUIDE.md  # Multi-engine setup guide
├── FORMATTING_GUIDE.md    # Formatting preservation guide
├── README.md             # This file
├── .gitignore            # Git ignore rules
├── templates/            # HTML templates
│   ├── index.html        # Main upload page
│   └── status.html       # Translation status page
├── uploads/              # Temporary upload directory
│   └── .gitkeep
└── translated/           # Temporary translated files directory
    └── .gitkeep
```

## 🚀 Installation

### 1. Clone or Navigate to the Project Directory

```bash
cd ..../PythonExamples/IA/llama_pdf_traslator
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3b. (Optional) Start LibreTranslate
Run this if you want to use the LibreTranslate engine instead of Llama/Copilot:
```bash
docker run -ti --rm -p 5001:5000 libretranslate/libretranslate --load-only en,it
```
If you change host/port, export `LIBRETRANSLATE_URL`, e.g.:
```bash
export LIBRETRANSLATE_URL=http://localhost:5001/translate
```

**Note**: Installing `llama-cpp-python` may take some time as it compiles C++ extensions. If you have a CUDA-capable GPU, you can install the GPU version:

```bash
# For CUDA GPU support (optional)
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### 4. Verify Model Path

Ensure the Llama 2 model file exists at:
```
/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf
```

If your model is in a different location, edit `app.py` and update the `MODEL_PATH` variable:

```python
MODEL_PATH = "/your/path/to/llama-2-7b.Q4_K_M.gguf"
```

## 🎯 Usage

### Starting the Application

1. **Activate the virtual environment** (if not already activated):
   ```bash
   source venv/bin/activate
   ```

2. **Run the Flask application**:
   ```bash
   python app.py
   ```

3. **Wait for model loading**: The application will load the Llama model, which may take 30-60 seconds:
   ```
   ============================================================
   PDF Translator with Llama Model
   ============================================================
   Initializing PDF Translator...
   Loading Llama model from /mnt/Virtuali/llama-2-7b.Q4_K_M.gguf...
   Model loaded successfully!
   
   Starting Flask server...
   Access the application at: http://localhost:5000
   ============================================================
   ```

4. **Open your web browser** and navigate to:
   ```
   http://localhost:5000
   ```

### Using the Web Interface

1. **Check Model Status**: Verify that the model is loaded (green badge at the top)

2. **Upload PDF**:
   - Click "Browse Files" or drag and drop a PDF file
   - Maximum file size: 16MB
   - Only PDF files are accepted

   **Choose engine**:
   - Llama (local model)
   - Copilot (cloud via GitHub Copilot CLI)
   - LibreTranslate (local REST; requires running container above)

3. **Start Translation**: Click "Translate to Italian" button

4. **Monitor Progress**: 
   - You'll be redirected to a status page
   - The page auto-refreshes every 3 seconds
   - Progress bar shows translation status

5. **Download Result**:
   - Once complete, click "Download Translated PDF"
   - The translated file will have "_italian" suffix
   - Example: `document.pdf` → `document_italian.pdf`

6. **Clean Up** (optional): Click "Clean Up" to remove temporary files

### Using the Python Class Directly

You can also use the translator class programmatically:

```python
from translator import PDFTranslator

# Initialize translator
translator = PDFTranslator(
    model_path="/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf",
    n_ctx=2048,
    n_threads=4
)

# Translate a PDF
success = translator.translate_pdf(
    input_pdf_path="input_document.pdf",
    output_pdf_path="output_document_italian.pdf"
)

if success:
    print("Translation completed successfully!")
else:
    print("Translation failed!")
```

## 🔧 Configuration

### Model Parameters

Edit `app.py` or `translator.py` to adjust model parameters:

```python
translator = PDFTranslator(
    model_path="/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf",
    n_ctx=2048,        # Context window size (higher = more context, more RAM)
    n_threads=4        # Number of CPU threads to use
)
```

### Translation Parameters

In `translator.py`, adjust the `_translate_chunk` method:

```python
response = self.llm(
    prompt,
    max_tokens=2048,     # Maximum tokens in response
    temperature=0.3,     # Lower = more deterministic (0.0-1.0)
    top_p=0.9,          # Nucleus sampling parameter
    echo=False,
    stop=["English text:", "Translate"]
)
```

### Flask Configuration

In `app.py`, modify Flask settings:

```python
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max upload size
app.secret_key = 'your-secret-key-here'  # Change for production!

# Run configuration
app.run(
    debug=True,          # Set to False in production
    host='0.0.0.0',     # Listen on all interfaces
    port=5000,          # Port number
    use_reloader=False  # Prevent model reload on code changes
)
```

## 📊 Performance Tips

1. **Hardware Recommendations**:
   - CPU: Modern multi-core processor (4+ cores recommended)
   - RAM: 8GB minimum, 16GB recommended
   - Storage: SSD for faster model loading

2. **Optimization**:
   - Use Q4_K_M quantized models for best balance of speed and quality
   - Adjust `n_threads` based on your CPU cores (usually # of physical cores)
   - Keep `n_ctx` at 2048 for most documents (increase for very long pages)

3. **Translation Speed**:
   - Average: 1-5 minutes per page
   - Depends on: page length, CPU speed, model size
   - Technical documents may take longer due to specialized terminology



# &lt; AlNao /&gt;
Tutti i codici sorgente e le informazioni presenti in questo repository sono frutto di un attento e paziente lavoro di sviluppo da parte di AlNao, che si è impegnato a verificarne la correttezza nella massima misura possibile. Qualora parte del codice o dei contenuti sia stato tratto da fonti esterne, la relativa provenienza viene sempre citata, nel rispetto della trasparenza e della proprietà intellettuale. 


Alcuni contenuti e porzioni di codice presenti in questo repository sono stati realizzati anche grazie al supporto di strumenti di intelligenza artificiale, il cui contributo ha permesso di arricchire e velocizzare la produzione del materiale. Ogni informazione e frammento di codice è stato comunque attentamente verificato e validato, con l’obiettivo di garantire la massima qualità e affidabilità dei contenuti offerti. 


Per ulteriori dettagli, approfondimenti o richieste di chiarimento, si invita a consultare il sito [AlNao.it](https://www.alnao.it/).


## License
Made with ❤️ by <a href="https://www.alnao.it">AlNao</a>
&bull; 
Public projects 
<a href="https://www.gnu.org/licenses/gpl-3.0"  valign="middle"> <img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=plastic" alt="GPL v3" valign="middle" /></a>
*Free Software!*


Il software è distribuito secondo i termini della GNU General Public License v3.0. L'uso, la modifica e la ridistribuzione sono consentiti, a condizione che ogni copia o lavoro derivato sia rilasciato con la stessa licenza. Il contenuto è fornito "così com'è", senza alcuna garanzia, esplicita o implicita.


The software is distributed under the terms of the GNU General Public License v3.0. Use, modification, and redistribution are permitted, provided that any copy or derivative work is released under the same license. The content is provided "as is", without any warranty, express or implied.

