// RAG Demo - Interactive API Testing
// Base URL for API calls
const BASE_URL = `http://${window.location.hostname}:8000`;

// Status management for navigation bar
function updateStatus(status, message) {
    const indicator = document.getElementById('statusIndicator');
    const text = document.getElementById('statusText');
    
    // Remove all status classes
    indicator.classList.remove('status-online', 'status-offline', 'status-checking');
    
    // Add appropriate status class
    indicator.classList.add(`status-${status}`);
    text.textContent = message;
}

// Debug function to test connectivity
function debugConnection() {
    console.log('Testing connection to:', BASE_URL);
    console.log('Current location:', window.location.href);
    
    // Create a modal or alert with debug info
    const debugInfo = `🔍 Debug Info:
Base URL: ${BASE_URL}
Current Location: ${window.location.href}
Hostname: ${window.location.hostname}
Protocol: ${window.location.protocol}
Port: ${window.location.port || 'default'}`;
    
    alert(debugInfo);
    console.log('Debug info:', debugInfo);
}

// Health Check (now runs in background for status indicator)
async function testHealth() {
    updateStatus('checking', 'Checking...');
    
    console.log('Calling health endpoint:', `${BASE_URL}/health`);
    
    try {
        const response = await fetch(`${BASE_URL}/health`);
        console.log('Health response status:', response.status);
        const data = await response.json();
        console.log('Health response data:', data);
        
        updateStatus('online', 'Online');
        
        return { success: true, data };
    } catch (error) {
        console.error('Health check error:', error);
        updateStatus('offline', 'Offline');
        
        return { success: false, error: error.message };
    }
}

// Document Ingestion
async function ingestDocument() {
    const resultDiv = document.getElementById('ingestResult');
    const fileInput = document.getElementById('fileInput');
    const docId = document.getElementById('docId').value;
    
    // Validation
    if (!fileInput.files[0]) {
        resultDiv.innerHTML = '<div class="alert alert-danger" role="alert">❌ Please select a file</div>';
        return;
    }
    
    if (!docId.trim()) {
        resultDiv.innerHTML = '<div class="alert alert-danger" role="alert">❌ Please enter a document ID</div>';
        return;
    }

    resultDiv.innerHTML = '<div class="alert alert-info result-loading" role="alert">📤 Uploading and indexing document...</div>';
    
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
            resultDiv.innerHTML = `<div class="alert alert-success result-success" role="alert">
                ✅ Document ingested successfully!
                <br><strong>File:</strong> ${fileInput.files[0].name}
                <br><strong>Document ID:</strong> ${docId}
                <hr>
                <pre class="mb-0">${JSON.stringify(data, null, 2)}</pre>
            </div>`;
            
            // Clear the form
            fileInput.value = '';
            document.getElementById('docId').value = '';
        } else {
            resultDiv.innerHTML = `<div class="alert alert-danger result-error" role="alert">❌ Ingestion Failed: ${data.detail || 'Unknown error'}</div>`;
        }
    } catch (error) {
        console.error('Ingest error:', error);
        resultDiv.innerHTML = `<div class="alert alert-danger result-error" role="alert">❌ Upload Error: ${error.message}</div>`;
    }
}

// Query Documents (RAG)
async function queryDocuments() {
    const resultDiv = document.getElementById('queryResult');
    const queryText = document.getElementById('queryText').value;
    const topK = document.getElementById('topK').value;
    
    if (!queryText.trim()) {
        resultDiv.innerHTML = '<div class="alert alert-danger" role="alert">❌ Please enter a question</div>';
        return;
    }
    
    resultDiv.innerHTML = '<div class="alert alert-info result-loading" role="alert">🔍 Searching documents...</div>';
    
    try {
        console.log('Querying with:', queryText, 'top-k:', topK);
        
        const response = await fetch(`${BASE_URL}/query?q=${encodeURIComponent(queryText.trim())}&k=${topK}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        console.log('Query response:', data);
        
        if (response.ok) {
            // Format the response nicely
            let formattedResponse = `<div class="alert alert-success result-success" role="alert">
                ✅ Query completed!
                <br><strong>Question:</strong> ${queryText}
                <br><strong>Results found:</strong> ${topK}`;
            
            if (data.answer) {
                formattedResponse += `<hr><h6>🤖 AI Answer:</h6>
                <div class="bg-light p-3 rounded">${data.answer}</div>`;
            }
            
            if (data.sources && data.sources.length > 0) {
                formattedResponse += `<hr><h6>📚 Sources:</h6><ol class="mb-0">`;
                data.sources.forEach((source, index) => {
                    formattedResponse += `<li><small>${source.content.substring(0, 150)}...</small></li>`;
                });
                formattedResponse += `</ol>`;
            }
            
            formattedResponse += `<hr><details>
                <summary><small>📋 Raw Response</small></summary>
                <pre class="mt-2 mb-0"><small>${JSON.stringify(data, null, 2)}</small></pre>
            </details></div>`;
            
            resultDiv.innerHTML = formattedResponse;
        } else {
            resultDiv.innerHTML = `<div class="alert alert-danger result-error" role="alert">❌ Query Failed: ${data.detail || 'Unknown error'}</div>`;
        }
    } catch (error) {
        console.error('Query error:', error);
        resultDiv.innerHTML = `<div class="alert alert-danger result-error" role="alert">❌ Search Error: ${error.message}</div>`;
    }
}

// Periodic health check
function startHealthMonitoring() {
    // Initial health check
    testHealth();
    
    // Check every 30 seconds
    setInterval(testHealth, 30000);
}

// Add keyboard shortcuts and event listeners
function setupEventListeners() {
    // Button event listeners
    document.getElementById('debugBtn').addEventListener('click', debugConnection);
    document.getElementById('ingestBtn').addEventListener('click', ingestDocument);
    document.getElementById('queryBtn').addEventListener('click', queryDocuments);
    
    // Enter key for query input
    document.getElementById('queryText').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            queryDocuments();
        }
    });
    
    // File input change event for auto-generating doc ID
    document.getElementById('fileInput').addEventListener('change', function(e) {
        const file = e.target.files[0];
        const docIdInput = document.getElementById('docId');
        
        if (file && !docIdInput.value.trim()) {
            // Auto-generate doc ID from filename
            const fileName = file.name.split('.')[0];
            const timestamp = new Date().toISOString().slice(0, 10);
            docIdInput.value = `${fileName}_${timestamp}`;
        }
    });
}

// Initialize the application
function initializeApp() {
    console.log('RAG Demo App Initialized');
    console.log('Base URL:', BASE_URL);
    
    // Setup event listeners
    setupEventListeners();
    
    // Start health monitoring
    startHealthMonitoring();
    
    // Add helpful tooltips using Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add tooltip to query input
    document.getElementById('queryText').title = 'Press Enter to search';
    
    console.log('✅ Application initialized successfully');
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
    updateStatus('offline', 'Error');
});

// Export functions for debugging in console
window.ragDemo = {
    testHealth,
    ingestDocument,
    queryDocuments,
    debugConnection,
    updateStatus,
    BASE_URL
};

// Add visibility change handler for health monitoring
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        // Page became visible, check health
        testHealth();
    }
});
