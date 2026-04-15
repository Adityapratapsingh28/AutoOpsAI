/**
 * AutoOps AI — Files Page Logic
 *
 * Handles file listing, upload, delete, LLM summarization,
 * and Q&A about files.
 */

if (!requireAuth()) throw new Error('Not authenticated');

let currentAskFileId = null;

// =========================================
// LOAD FILES
// =========================================

async function loadFiles() {
    try {
        const files = await apiGet('/files');
        const container = document.getElementById('fileList');
        const countEl = document.getElementById('fileCount');

        if (files.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="grid-column:1/-1;">
                    <div class="icon">📂</div>
                    <h3>No files yet</h3>
                    <p>Upload a CSV file to get started</p>
                </div>`;
            countEl.textContent = '0 files';
            return;
        }

        countEl.textContent = `${files.length} file${files.length !== 1 ? 's' : ''}`;
        container.innerHTML = files.map(f => {
            const ext = (f.file_name || '').split('.').pop().toLowerCase();
            const icon = getFileIcon(ext);
            return `
            <div class="file-card" id="file-card-${f.id}">
                <div class="file-icon">${icon}</div>
                <div class="file-info">
                    <div class="name">${escapeHtml(f.file_name)}</div>
                    <div class="meta">${formatDate(f.created_at)}</div>
                </div>
                <div class="file-actions">
                    <button class="btn btn-ghost btn-sm" onclick="summarizeFile(${f.id}, '${escapeHtml(f.file_name)}')" title="Summarize">📊</button>
                    <button class="btn btn-ghost btn-sm" onclick="openAskPanel(${f.id}, '${escapeHtml(f.file_name)}')" title="Ask about this file">💬</button>
                    <button class="btn btn-ghost btn-sm" onclick="deleteFile(${f.id})" title="Delete">🗑️</button>
                </div>
            </div>
        `}).join('');

    } catch (err) {
        showToast('Failed to load files: ' + err.message, 'error');
    }
}

function getFileIcon(ext) {
    const icons = {
        csv: '📊', xlsx: '📊', xls: '📊',
        json: '📋', txt: '📝', md: '📝',
        pdf: '📕', docx: '📘', doc: '📘',
        py: '🐍', js: '🟨', html: '🌐',
    };
    return icons[ext] || '📄';
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// =========================================
// UPLOAD
// =========================================

function handleDragOver(e) {
    e.preventDefault();
    document.getElementById('uploadZone').classList.add('dragover');
}

function handleDragLeave(e) {
    document.getElementById('uploadZone').classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    document.getElementById('uploadZone').classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) doUpload(file);
}

async function uploadFile(e) {
    const file = e.target.files[0];
    if (file) doUpload(file);
}

async function doUpload(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        await apiUpload('/files/upload', formData);
        showToast(`"${file.name}" uploaded`, 'success');
        loadFiles();
    } catch (err) {
        showToast('Upload failed: ' + err.message, 'error');
    }
}

// =========================================
// DELETE
// =========================================

async function deleteFile(id) {
    if (!confirm('Delete this file?')) return;
    try {
        await apiDelete(`/files/${id}`);
        showToast('File deleted', 'success');
        loadFiles();
    } catch (err) {
        showToast('Delete failed: ' + err.message, 'error');
    }
}

// =========================================
// SUMMARIZE (LLM-powered)
// =========================================

async function summarizeFile(fileId, fileName) {
    const panel = document.getElementById('fileInsightPanel');
    const titleEl = document.getElementById('insightTitle');
    const contentEl = document.getElementById('insightContent');

    panel.style.display = 'block';
    titleEl.textContent = `📊 Summarizing: ${fileName}`;
    contentEl.innerHTML = '<span style="color:var(--text-muted);animation:pulse-dot 1.5s infinite;">⏳ Generating AI summary... this may take a few seconds</span>';

    // Scroll into view
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

    try {
        const result = await apiPost(`/files/${fileId}/summarize`, {});

        if (result.summary) {
            titleEl.textContent = `📊 Summary: ${fileName}`;
            contentEl.innerHTML = renderMarkdown(result.summary);
        } else {
            contentEl.textContent = 'Summary generated but empty.';
        }
    } catch (err) {
        contentEl.textContent = `❌ Failed: ${err.message}`;
        showToast('Summarize failed: ' + err.message, 'error');
    }
}

function closeInsight() {
    document.getElementById('fileInsightPanel').style.display = 'none';
}

// =========================================
// ASK ABOUT FILE (Q&A Chat)
// =========================================

function openAskPanel(fileId, fileName) {
    currentAskFileId = fileId;
    document.getElementById('askFileName').textContent = fileName;
    document.getElementById('askChat').innerHTML = `
        <div class="chat-msg bot">
            <div class="chat-bubble">Hi! I can answer questions about <strong>${escapeHtml(fileName)}</strong>. What would you like to know?</div>
        </div>
    `;
    document.getElementById('askPanel').style.display = 'block';
    document.getElementById('askInput').value = '';
    document.getElementById('askInput').focus();
    document.getElementById('askPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function closeAskPanel() {
    currentAskFileId = null;
    document.getElementById('askPanel').style.display = 'none';
}

async function askQuestion() {
    if (!currentAskFileId) return;

    const input = document.getElementById('askInput');
    const question = input.value.trim();
    if (!question) return;

    const chat = document.getElementById('askChat');

    // Show user message
    chat.innerHTML += `<div class="chat-msg user"><div class="chat-bubble">${escapeHtml(question)}</div></div>`;
    input.value = '';

    // Show loading
    const loadingId = 'loading-' + Date.now();
    chat.innerHTML += `<div class="chat-msg bot" id="${loadingId}"><div class="chat-bubble" style="color:var(--text-muted);">⏳ Thinking...</div></div>`;
    chat.scrollTop = chat.scrollHeight;

    try {
        const result = await apiPost(`/files/${currentAskFileId}/ask`, { question });
        const loadingEl = document.getElementById(loadingId);

        if (result.answer) {
            loadingEl.querySelector('.chat-bubble').innerHTML = renderMarkdown(result.answer);
        } else {
            loadingEl.querySelector('.chat-bubble').textContent = 'I could not find an answer in the file.';
        }
    } catch (err) {
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) {
            loadingEl.querySelector('.chat-bubble').textContent = `❌ Error: ${err.message}`;
        }
    }

    chat.scrollTop = chat.scrollHeight;
}

// =========================================
// MARKDOWN RENDERER (shared with workflow)
// =========================================

function renderMarkdown(text) {
    let html = escapeHtml(text);
    html = html.replace(/^#{1,4}\s+(.+)$/gm, '<strong class="md-heading">$1</strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/^[-•]\s+(.+)$/gm, '<span class="md-bullet">• $1</span>');
    html = html.replace(/^(\d+)\.\s+(.+)$/gm, '<span class="md-bullet">$1. $2</span>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

// =========================================
// INIT
// =========================================

loadFiles();
