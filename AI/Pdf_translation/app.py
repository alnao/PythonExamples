"""
Flask Application for PDF Translation
Web interface to upload English PDFs and download Italian translations.
"""

import os
import uuid
import subprocess
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from translator import PDFTranslator
import threading
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TRANSLATED_FOLDER'] = 'translated'

# Model configuration
MODEL_PATH = "/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf"
LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL", "http://localhost:5001/translate")
    # docker run -ti --rm -p 5001:5000 libretranslate/libretranslate
    # docker run -ti --rm -p 5001:5000 libretranslate/libretranslate --load-only en,it

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

# Global translator instances (loaded based on selection)
llama_translator = None
copilot_translator = None
libre_translator = None

# Dictionary to track translation jobs
translation_jobs = {}


def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def initialize_llama_translator():
    """Initialize the translator with the Llama model."""
    global llama_translator
    try:
        print("Initializing Llama PDF Translator...")
        llama_translator = PDFTranslator(
            model_path=MODEL_PATH, 
            n_ctx=2048, 
            n_threads=4,
            translation_engine="llama"
        )
        print("Llama Translator initialized successfully!")
        return True
    except Exception as e:
        print(f"Error initializing Llama translator: {e}")
        return False


def initialize_copilot_translator(model: str = "gpt-5"):
    """Initialize the translator with GitHub Copilot CLI."""
    try:
        print(f"Initializing GitHub Copilot CLI Translator with model: {model}...")
        translator = PDFTranslator(translation_engine="copilot", copilot_model=model)
        print("Copilot Translator initialized successfully!")
        return translator
    except Exception as e:
        print(f"Error initializing Copilot translator: {e}")
        return None


def initialize_libre_translator():
    """Initialize the translator for LibreTranslate (no heavy init)."""
    try:
        print(f"Initializing LibreTranslate client at {LIBRETRANSLATE_URL}...")
        translator = PDFTranslator(translation_engine="libre", libretranslate_url=LIBRETRANSLATE_URL)
        print("LibreTranslate client configured!")
        return translator
    except Exception as e:
        print(f"Error initializing LibreTranslate translator: {e}")
        return None


def get_translator(engine: str, copilot_model: str = "gpt-5"):
    """Get the appropriate translator instance."""
    if engine == "llama":
        return llama_translator
    elif engine == "copilot":
        # Create a new instance with the selected model
        return initialize_copilot_translator(copilot_model)
    elif engine == "libre":
        return initialize_libre_translator()
    return None


def build_blocks(translator: PDFTranslator, input_path: str, two_columns: bool = False) -> list:
    """Extract text blocks for user review."""
    pages_data = translator.extract_text_from_pdf(input_path, two_columns=two_columns)
    blocks = []

    for page_data in pages_data:
        page_num = page_data["page_num"]
        page_blocks = page_data["blocks"]
        print(f"Page {page_num} has {len(page_blocks)} text blocks.")
        for block in page_blocks:
            original_text = block.get("text", "").strip()
            format = block.get("format", {})
            if original_text:
                blocks.append({
                    "page": page_num,
                    "text": original_text,
                    "length": len(original_text),
                    "format": format
                })

    return blocks


def translate_in_background(job_id, input_path, output_path, engine, copilot_model=None, two_columns: bool = False):
    """Background task to translate PDF."""
    global translation_jobs
    
    translation_jobs[job_id]['status'] = 'processing'
    translation_jobs[job_id]['progress'] = 10
    
    try:
        translator = get_translator(engine, copilot_model or "gpt-5")
        if translator is None:
            translation_jobs[job_id]['status'] = 'failed'
            translation_jobs[job_id]['error'] = f'Translator engine "{engine}" not available.'
            return
        
        # Perform translation
        success = translator.translate_pdf(input_path, output_path, two_columns=two_columns)
        
        if success:
            translation_jobs[job_id]['status'] = 'completed'
            translation_jobs[job_id]['progress'] = 100
            translation_jobs[job_id]['output_file'] = output_path
        else:
            translation_jobs[job_id]['status'] = 'failed'
            translation_jobs[job_id]['error'] = 'Translation failed. Please check the logs.'
    
    except Exception as e:
        translation_jobs[job_id]['status'] = 'failed'
        translation_jobs[job_id]['error'] = str(e)
        print(f"Translation error: {e}")


@app.route('/')
def index():
    """Render the main page."""
    llama_loaded = llama_translator is not None
    copilot_available = copilot_translator is not None
    libre_available = True  # Assume service reachable on same server
    
    # Try to check if copilot is available without full initialization
    if not copilot_available:
        try:
            result = subprocess.run(
                ["copilot", "--version"], #["gh", "copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=2
            )
            print(f"GitHub Copilot CLI check: {result.stdout.strip()}")
            if result.returncode != 0:
                print("GitHub Copilot CLI not available (non-zero return code)")
                # print("Error output:", result.stderr.strip())
                # print("RUN \"gh extension install github/gh-copilot\" to install the CLI extension.")
            copilot_available = result.returncode == 0
        except:
            copilot_available = False
    
    return render_template('index.html', 
                         llama_loaded=llama_loaded, 
                         copilot_available=copilot_available,
                         libre_available=libre_available)


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    """Handle files exceeding the configured upload limit."""
    flash('File too large. Maximum allowed size is 64MB.', 'danger')
    return redirect(url_for('index'))


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start translation."""
    # Get selected engine
    engine = request.form.get('engine', 'llama')
    column_layout = request.form.get('column_layout', 'single')
    two_columns = column_layout == 'double'
    
    # Get Copilot model if using Copilot engine
    copilot_model = request.form.get('copilot_model', 'gpt-5') if engine == 'copilot' else None
    
    # Check if appropriate translator is initialized
    translator = get_translator(engine, copilot_model)
    if translator is None and engine == "llama":
        flash('Llama model not loaded. Please wait for initialization or restart the server.', 'danger')
        return redirect(url_for('index'))
    elif translator is None and engine == "copilot":
        flash('GitHub Copilot CLI not available. Please check installation.', 'danger')
        return redirect(url_for('index'))
    elif translator is None and engine == "libre":
        flash('LibreTranslate service not reachable. Please ensure it is running on this server.', 'danger')
        return redirect(url_for('index'))
    
    # Check if file is present
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    # Check if file is selected
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('index'))
    
    # Check if file is allowed
    if file and allowed_file(file.filename):
        # Generate unique filenames
        job_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        base_name = os.path.splitext(filename)[0]
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
        output_filename = f"{base_name}_italian.pdf"
        output_path = os.path.join(app.config['TRANSLATED_FOLDER'], f"{job_id}_{output_filename}")
        
        # Save uploaded file
        file.save(input_path)

        # Build preview blocks before starting translation
        try:
            blocks = build_blocks(translator, input_path, two_columns=two_columns)
        except Exception as e:
            flash(f'Error while preparing text blocks: {e}', 'danger')
            return redirect(url_for('index'))

        if not blocks:
            flash('Unable to extract text from PDF for preview.', 'danger')
            return redirect(url_for('index'))
        
        # Create job tracking (awaiting user approval)
        translation_jobs[job_id] = {
            'status': 'awaiting_approval',
            'progress': 0,
            'input_file': input_path,
            'output_file': None,
            'output_filename': output_filename,
            'engine': engine,
            'copilot_model': copilot_model,
            'blocks': blocks,
            'two_columns': two_columns,
            'column_layout': column_layout,
            'error': None,
            'timestamp': time.time()
        }
        
        flash('File uploaded. Review the detected blocks before starting translation.', 'info')
        return redirect(url_for('review_blocks', job_id=job_id))
    
    else:
        flash('Invalid file type. Please upload a PDF file.', 'danger')
        return redirect(url_for('index'))


@app.route('/status/<job_id>')
def status(job_id):
    """Show translation status page."""
    if job_id not in translation_jobs:
        flash('Invalid job ID', 'danger')
        return redirect(url_for('index'))
    
    job = translation_jobs[job_id]
    return render_template('status.html', job_id=job_id, job=job)


@app.route('/blocks/<job_id>')
def review_blocks(job_id):
    """Display block list and ask for approval before translation."""
    if job_id not in translation_jobs:
        flash('Invalid job ID', 'danger')
        return redirect(url_for('index'))

    job = translation_jobs[job_id]
    if job.get('status') != 'awaiting_approval':
        return redirect(url_for('status', job_id=job_id))

    blocks = job.get('blocks', [])
    return render_template('chunk_review.html', job_id=job_id, job=job, blocks=blocks)


@app.route('/approve/<job_id>', methods=['POST'])
def approve_blocks(job_id):
    """User approved blocks: start translation."""
    if job_id not in translation_jobs:
        flash('Invalid job ID', 'danger')
        return redirect(url_for('index'))

    job = translation_jobs[job_id]
    if job.get('status') != 'awaiting_approval':
        return redirect(url_for('status', job_id=job_id))

    job['status'] = 'queued'
    job['progress'] = 0

    # Start translation in background now
    thread = threading.Thread(
        target=translate_in_background,
        args=(
            job_id,
            job['input_file'],
            os.path.join(app.config['TRANSLATED_FOLDER'], f"{job_id}_{job['output_filename']}"),
            job['engine'],
            job.get('copilot_model'),
            job.get('two_columns', False)
        )
    )
    thread.daemon = True
    thread.start()

    flash('Blocks approved. Translation started.', 'success')
    return redirect(url_for('status', job_id=job_id))


@app.route('/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id):
    """Cancel a job before translation starts."""
    if job_id not in translation_jobs:
        flash('Invalid job ID', 'danger')
        return redirect(url_for('index'))

    job = translation_jobs.pop(job_id)

    # Clean up files
    for path in [job.get('input_file'), job.get('output_file')]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    flash('Translation canceled and files removed.', 'info')
    return redirect(url_for('index'))


@app.route('/api/status/<job_id>')
def api_status(job_id):
    """API endpoint to check translation status."""
    if job_id not in translation_jobs:
        return jsonify({'error': 'Invalid job ID'}), 404
    
    job = translation_jobs[job_id]
    return jsonify({
        'status': job['status'],
        'progress': job['progress'],
        'error': job['error']
    })


@app.route('/download/<job_id>')
def download_file(job_id):
    """Handle file download."""
    if job_id not in translation_jobs:
        flash('Invalid job ID', 'danger')
        return redirect(url_for('index'))
    
    job = translation_jobs[job_id]
    
    if job['status'] != 'completed':
        flash('Translation not completed yet', 'warning')
        return redirect(url_for('status', job_id=job_id))
    
    output_path = job['output_file']
    output_filename = job['output_filename']
    
    if not os.path.exists(output_path):
        flash('Translated file not found', 'danger')
        return redirect(url_for('index'))
    
    return send_file(
        output_path,
        as_attachment=True,
        download_name=output_filename,
        mimetype='application/pdf'
    )


@app.route('/cleanup/<job_id>', methods=['POST'])
def cleanup(job_id):
    """Clean up translation files."""
    if job_id in translation_jobs:
        job = translation_jobs[job_id]
        
        # Delete files
        try:
            if os.path.exists(job['input_file']):
                os.remove(job['input_file'])
            if job['output_file'] and os.path.exists(job['output_file']):
                os.remove(job['output_file'])
        except Exception as e:
            print(f"Error cleaning up files: {e}")
        
        # Remove from tracking
        del translation_jobs[job_id]
        flash('Files cleaned up successfully', 'info')
    
    return redirect(url_for('index'))


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'llama_loaded': llama_translator is not None,
        'copilot_available': copilot_translator is not None,
        'libre_available': True,
        'active_jobs': len([j for j in translation_jobs.values() if j['status'] in ['queued', 'processing']])
    })


def cleanup_old_jobs():
    """Clean up old translation jobs (called periodically)."""
    current_time = time.time()
    max_age = 3600  # 1 hour
    
    jobs_to_remove = []
    for job_id, job in translation_jobs.items():
        if current_time - job['timestamp'] > max_age:
            # Delete files
            try:
                if os.path.exists(job['input_file']):
                    os.remove(job['input_file'])
                if job['output_file'] and os.path.exists(job['output_file']):
                    os.remove(job['output_file'])
            except Exception as e:
                print(f"Error cleaning up old job {job_id}: {e}")
            
            jobs_to_remove.append(job_id)
    
    for job_id in jobs_to_remove:
        del translation_jobs[job_id]
        print(f"Cleaned up old job: {job_id}")


if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TRANSLATED_FOLDER'], exist_ok=True)
    
    # Initialize translators
    print("="*60)
    print("PDF Translator - Multi-Engine Support")
    print("="*60)
    
    # Try to initialize Llama
    llama_status = initialize_llama_translator()
    
    # Check if Copilot CLI is available (without creating instance)
    copilot_status = False
    try:
        result = subprocess.run(
            ["gh", "copilot", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        copilot_status = result.returncode == 0
        if copilot_status:
            print("GitHub Copilot CLI detected!")
    except Exception as e:
        print(f"GitHub Copilot CLI not available: {e}")
    
    if llama_status or copilot_status:
        print("\nStarting Flask server...")
        print("Access the application at: http://localhost:5000")
        if llama_status:
            print("✓ Llama translator available")
        if copilot_status:
            print("✓ GitHub Copilot CLI translator available")
        print("="*60)
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    else:
        print("\n⚠ Warning: No translation engines available!")
        print("- For Llama: Check model path and installation")
        print("- For Copilot: Install GitHub CLI and authenticate")
        print("\nStarting server anyway (you can initialize engines later)...")
        print("="*60)
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
        print("\nFailed to initialize translator. Please check the model path.")
        print(f"Model path: {MODEL_PATH}")
