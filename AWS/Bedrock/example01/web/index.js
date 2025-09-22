// RAG Demo - Interactive API Testing
// Base URL for API calls
const BASE_URL = `http://${window.location.hostname}:8000`;

// Debug function to test connectivity
function debugConnection() {
    console.log('Testing connection to:', BASE_URL);
    console.log('Current location:', window.location.href);
    
    // Show debug info in the health result div
    const resultDiv = document.getElementById('healthResult');
    resultDiv.innerHTML = `<div class="success">🔍 Debug Info:
    <br>Base URL: ${BASE_URL}
    <br>Current Location: ${window.location.href}
    <br>Hostname: ${window.location.hostname}
    <br>Protocol: ${window.location.protocol}
    <br>Port: ${window.location.port || 'default'}</div>`;
}

// Health Check
async function testHealth() {
    const resultDiv = document.getElementById('healthResult');
    resultDiv.innerHTML = '<div class="loading">Testing health endpoint...</div>';
    
    console.log('Calling health endpoint:', `${BASE_URL}/health`);
    
    try {
        const response = await fetch(`${BASE_URL}/health`);
        console.log('Health response status:', response.status);
        const data = await response.json();
        console.log('Health response data:', data);
        resultDiv.innerHTML = `<div class="success">✅ Health Check Successful!
        <pre>${JSON.stringify(data, null, 2)}</pre></div>`;
    } catch (error) {
        console.error('Health check error:', error);
        resultDiv.innerHTML = `<div class="error">❌ Health Check Failed: ${error.message}
        <br><br>Possible issues:
        <br>• FastAPI service not running on port 8000
        <br>• CORS policy blocking the request
        <br>• Network connectivity issues</div>`;
    }
}

// Document Ingestion
async function ingestDocument() {
    const resultDiv = document.getElementById('ingestResult');
    const fileInput = document.getElementById('fileInput');
    const docId = document.getElementById('docId').value;
    
    // Validation
    if (!fileInput.files[0]) {
        resultDiv.innerHTML = '<div class="error">❌ Please select a file</div>';
        return;
    }
    
    if (!docId.trim()) {
        resultDiv.innerHTML = '<div class="error">❌ Please enter a document ID</div>';
        return;
    }

    resultDiv.innerHTML = '<div class="loading">📤 Uploading and indexing document...</div>';
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('doc_id', docId.trim());

    try {
        console.log('Uploading file:', fileInput.files[0].name, 'with ID:', docId);
        
        const response = await fetch(`${BASE_URL}/ingest`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        console.log('Ingest response:', data);
        
        if (response.ok) {
            resultDiv.innerHTML = `<div class="success">✅ Document ingested successfully!
            <br><strong>File:</strong> ${fileInput.files[0].name}
            <br><strong>Document ID:</strong> ${docId}
            <pre>${JSON.stringify(data, null, 2)}</pre></div>`;
            
            // Clear the form
            fileInput.value = '';
            document.getElementById('docId').value = '';
        } else {
            resultDiv.innerHTML = `<div class="error">❌ Ingestion Failed: ${data.detail || 'Unknown error'}</div>`;
        }
    } catch (error) {
        console.error('Ingest error:', error);
        resultDiv.innerHTML = `<div class="error">❌ Upload Error: ${error.message}</div>`;
    }
}

// Query Documents (RAG)
async function queryDocuments() {
    const resultDiv = document.getElementById('queryResult');
    const queryText = document.getElementById('queryText').value;
    const topK = document.getElementById('topK').value;
    
    if (!queryText.trim()) {
        resultDiv.innerHTML = '<div class="error">❌ Please enter a question</div>';
        return;
    }
    
    resultDiv.innerHTML = '<div class="loading">🔍 Searching documents...</div>';
    
    try {
        console.log('Querying with:', queryText, 'top-k:', topK);
        
        const response = await fetch(`${BASE_URL}/query?q=${encodeURIComponent(queryText.trim())}&k=${topK}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        console.log('Query response:', data);
        
        if (response.ok) {
            // Format the response nicely
            let formattedResponse = `<div class="success">✅ Query completed!
            <br><strong>Question:</strong> ${queryText}
            <br><strong>Results found:</strong> ${topK}`;
            
            if (data.answer) {
                formattedResponse += `<br><br><strong>🤖 AI Answer:</strong>
                <br>${data.answer}`;
            }
            
            if (data.sources && data.sources.length > 0) {
                formattedResponse += `<br><br><strong>📚 Sources:</strong>`;
                data.sources.forEach((source, index) => {
                    formattedResponse += `<br>${index + 1}. ${source.content.substring(0, 100)}...`;
                });
            }
            
            formattedResponse += `<br><br><strong>📋 Raw Response:</strong>
            <pre>${JSON.stringify(data, null, 2)}</pre></div>`;
            
            resultDiv.innerHTML = formattedResponse;
        } else {
            resultDiv.innerHTML = `<div class="error">❌ Query Failed: ${data.detail || 'Unknown error'}</div>`;
        }
    } catch (error) {
        console.error('Query error:', error);
        resultDiv.innerHTML = `<div class="error">❌ Search Error: ${error.message}</div>`;
    }
}

// Generate Response (Direct AI)
async function generateResponse() {
    const resultDiv = document.getElementById('generateResult');
    const promptText = document.getElementById('promptText').value;
    
    if (!promptText.trim()) {
        resultDiv.innerHTML = '<div class="error">❌ Please enter a prompt</div>';
        return;
    }
    
    resultDiv.innerHTML = '<div class="loading">🧠 Generating AI response...</div>';
    
    try {
        console.log('Generating response for prompt:', promptText);
        
        const response = await fetch(`${BASE_URL}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt: promptText.trim() })
        });
        
        const data = await response.json();
        console.log('Generate response:', data);
        
        if (response.ok) {
            resultDiv.innerHTML = `<div class="success">✅ Response generated!
            <br><strong>Prompt:</strong> ${promptText}
            <br><br><strong>🤖 AI Response:</strong>
            <br>${data.response || data.text || 'No response text found'}
            <br><br><strong>📋 Raw Response:</strong>
            <pre>${JSON.stringify(data, null, 2)}</pre></div>`;
        } else {
            resultDiv.innerHTML = `<div class="error">❌ Generation Failed: ${data.detail || 'Unknown error'}</div>`;
        }
    } catch (error) {
        console.error('Generate error:', error);
        resultDiv.innerHTML = `<div class="error">❌ Generation Error: ${error.message}</div>`;
    }
}

// Add keyboard shortcuts and event listeners
function setupEventListeners() {
    // Button event listeners
    document.getElementById('healthBtn').addEventListener('click', testHealth);
    document.getElementById('debugBtn').addEventListener('click', debugConnection);
    document.getElementById('ingestBtn').addEventListener('click', ingestDocument);
    document.getElementById('queryBtn').addEventListener('click', queryDocuments);
    document.getElementById('generateBtn').addEventListener('click', generateResponse);
    
    // Enter key for query input
    document.getElementById('queryText').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            queryDocuments();
        }
    });
    
    // Ctrl+Enter for generate textarea
    document.getElementById('promptText').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            generateResponse();
        }
    });
}

// Initialize the application
function initializeApp() {
    console.log('RAG Demo App Initialized');
    console.log('Base URL:', BASE_URL);
    
    // Setup event listeners
    setupEventListeners();
    
    // Test health on page load
    testHealth();
    
    // Add helpful tooltips
    document.getElementById('promptText').title = 'Tip: Use Ctrl+Enter to generate response';
    document.getElementById('queryText').title = 'Tip: Press Enter to search';
}

// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

// Export functions for debugging in console
window.ragDemo = {
    testHealth,
    ingestDocument,
    queryDocuments,
    generateResponse,
    debugConnection,
    BASE_URL
};
