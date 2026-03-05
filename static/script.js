document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('pdfFile');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInfo = document.getElementById('fileInfo');
    const fileNameDisplay = fileInfo.querySelector('.file-name');
    const removeFileBtn = document.getElementById('removeFileBtn');
    const statusMsg = document.getElementById('uploadStatus');
    
    const summarizeBtn = document.getElementById('summarizeBtn');
    const promptInput = document.getElementById('promptInput');
    const summaryOutput = document.getElementById('summaryOutput');
    const loadingState = document.getElementById('loadingState');
    
    let currentUploadedFilename = null;

    // --- Drag and Drop Logic ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => {
            dropArea.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => {
            dropArea.classList.remove('dragover');
        });
    });

    dropArea.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length === 0) return;
        
        const file = files[0];
        
        // Validate it's a PDF
        if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
            showStatus('Please upload a valid PDF file.', 'error');
            return;
        }

        // Show file info
        fileNameDisplay.textContent = file.name;
        
        // UI toggle
        Array.from(dropArea.children).forEach(el => {
            if(el.id !== 'fileInfo' && el.id !== 'pdfFile') el.classList.add('hidden');
        });
        fileInfo.classList.remove('hidden');
        
        // Enable upload
        uploadBtn.disabled = false;
        statusMsg.textContent = '';
        
        // Attach file to an invisible variable so the upload process can find it easily
        fileInput.files = files; // this works if dt.files was attached, though not strictly required as we can keep it in state
    }

    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // prevent triggering click on parent
        
        // Reset state
        fileInput.value = '';
        currentUploadedFilename = null;
        
        // UI restore
        fileInfo.classList.add('hidden');
        Array.from(dropArea.children).forEach(el => {
            if(el.id !== 'fileInfo' && el.id !== 'pdfFile') el.classList.remove('hidden');
        });
        
        uploadBtn.disabled = true;
        summarizeBtn.disabled = true;
        statusMsg.textContent = '';
        
        summaryOutput.classList.add('empty');
        summaryOutput.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🤖</span>
                <p>Your summary will appear here once generated.</p>
            </div>
        `;
    });

    // --- Upload Process ---
    uploadBtn.addEventListener('click', async () => {
        const file = fileInput.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        const btnText = uploadBtn.querySelector('.btn-text');
        const spinner = uploadBtn.querySelector('.spinner-small');

        try {
            // UI Loading state
            uploadBtn.disabled = true;
            btnText.textContent = 'Uploading...';
            spinner.classList.remove('hidden');
            statusMsg.textContent = '';
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                currentUploadedFilename = data.filename;
                showStatus('✓ PDF stored safely. Ready to summarize.', 'success');
                summarizeBtn.disabled = false;
            } else {
                showStatus(data.detail || 'Upload failed.', 'error');
                uploadBtn.disabled = false;
            }
        } catch (error) {
            showStatus('🚨 Server connection failed.', 'error');
            uploadBtn.disabled = false;
        } finally {
            btnText.textContent = 'Upload Document';
            spinner.classList.add('hidden');
        }
    });

    // --- MCP / Summarization Process ---
    summarizeBtn.addEventListener('click', async () => {
        if (!currentUploadedFilename) return;

        try {
            // UI state
            summarizeBtn.disabled = true;
            summaryOutput.classList.add('hidden');
            loadingState.classList.remove('hidden');
            
            const reqBody = {
                filename: currentUploadedFilename,
                prompt: promptInput.value || "Summarize this document"
            };
            
            const response = await fetch('/summarize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(reqBody)
            });
            
            const data = await response.json();
            
            summaryOutput.classList.remove('empty');
            
            if (response.ok) {
                // Parse markdown!
                const htmlContent = marked.parse(data.summary);
                summaryOutput.innerHTML = htmlContent;
            } else {
                // Formatting errors with a nice div
                summaryOutput.innerHTML = `
                    <div style="background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); padding: 1rem; border-radius: 8px; color: #ef4444;">
                        <strong>Error Generate Summary:</strong><br/>
                        ${data.detail || 'The AI model could not generate a summary.'}
                    </div>
                `;
            }
        } catch (error) {
            summaryOutput.innerHTML = `
                <div style="background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; padding: 1rem; color: #ef4444;">
                    <strong>Connection Error:</strong><br/>
                    Failed to reach the backend to start the MCP process. Is the server running?
                </div>
            `;
        } finally {
            summarizeBtn.disabled = false;
            loadingState.classList.add('hidden');
            summaryOutput.classList.remove('hidden');
            summaryOutput.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    });

    function showStatus(message, type) {
        statusMsg.textContent = message;
        statusMsg.className = `status-msg status-${type}`;
    }
});
