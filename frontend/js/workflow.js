/**
 * AutoOps AI — Workflow Page Logic (CORE)
 *
 * Handles:
 *   - Workflow input + file upload
 *   - POST /workflow/run → get workflow_id
 *   - SSE connection to /workflow/stream/{id}
 *   - Real-time agent card updates
 *   - DAG visualization (SVG)
 *   - Live log streaming
 *   - Final output display
 */

if (!requireAuth()) throw new Error('Not authenticated');

let currentWorkflowId = null;
let uploadedFileId = null;
let agents = [];

// ── Check for pre-filled prompt from URL ──
const urlParams = new URLSearchParams(window.location.search);
const prefillPrompt = urlParams.get('prompt');
if (prefillPrompt) {
    document.getElementById('workflowInput').value = prefillPrompt;
}

// =========================================
// FILE UPLOAD
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
    if (file) processFile(file);
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) processFile(file);
}

document.getElementById('uploadZone').addEventListener('click', () => {
    document.getElementById('fileInput').click();
});

async function processFile(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        const result = await apiUpload('/files/upload', formData);

        uploadedFileId = result.id;
        document.getElementById('uploadZone').classList.add('hidden');
        document.getElementById('fileAttached').classList.remove('hidden');
        document.getElementById('fileName').textContent = file.name;

        showToast(`File "${file.name}" uploaded successfully`, 'success');
    } catch (err) {
        showToast('File upload failed: ' + err.message, 'error');
    }
}

function removeFile() {
    uploadedFileId = null;
    document.getElementById('uploadZone').classList.remove('hidden');
    document.getElementById('fileAttached').classList.add('hidden');
}

// =========================================
// RUN WORKFLOW
// =========================================

async function runWorkflow() {
    const input = document.getElementById('workflowInput').value.trim();
    if (!input) {
        showToast('Please describe your workflow', 'error');
        return;
    }

    const runBtn = document.getElementById('runBtn');
    runBtn.disabled = true;
    runBtn.innerHTML = '⏳ Starting...';

    // Reset UI
    agents = [];
    document.getElementById('agentList').innerHTML = '';
    document.getElementById('agentEmpty')?.remove();
    document.getElementById('logsTerminal').innerHTML = '';
    // Reset report panel
    document.getElementById('reportPanel').style.display = 'none';
    document.getElementById('analysisSummary').style.display = 'none';
    document.getElementById('analysisSummary').innerHTML = '';
    document.getElementById('reportCard').style.display = 'none';
    document.getElementById('reportText').textContent = '';
    document.getElementById('rawOutputCard').style.display = 'none';
    document.getElementById('outputContent').textContent = '';
    document.getElementById('executionSection').classList.remove('hidden');

    addLog('Submitting workflow to orchestrator...', 'info');

    try {
        const result = await apiPost('/workflow/run', {
            input_text: input,
            file_id: uploadedFileId,
        });

        currentWorkflowId = result.workflow_id;
        addLog(`Workflow ${currentWorkflowId} started`, 'success');
        document.getElementById('runStatus').textContent = `ID: ${currentWorkflowId.slice(0, 8)}...`;

        // Open SSE stream
        connectSSE(currentWorkflowId);

    } catch (err) {
        addLog('Failed to start workflow: ' + err.message, 'error');
        showToast('Workflow start failed: ' + err.message, 'error');
        runBtn.disabled = false;
        runBtn.innerHTML = 'Run Workflow';
    }
}

// =========================================
// SSE STREAMING
// =========================================

function connectSSE(workflowId) {
    const url = `${API_BASE}/workflow/stream/${workflowId}`;
    const eventSource = new EventSource(url);

    document.getElementById('logStatus').innerHTML = '<span class="badge-dot"></span> Live';

    eventSource.onmessage = function(event) {
        try {
            const payload = JSON.parse(event.data);
            const eventType = payload.event;
            const data = payload.data;

            handleSSEEvent(eventType, data);

            if (eventType === 'done' || eventType === 'error') {
                eventSource.close();
                onWorkflowComplete(eventType === 'error');
            }
        } catch (e) {
            console.warn('SSE parse error:', e);
        }
    };

    eventSource.onerror = function() {
        eventSource.close();
        addLog('SSE connection closed', 'warning');
        onWorkflowComplete(false);
    };
}

function handleSSEEvent(eventType, data) {
    switch (eventType) {
        case 'status':
            addLog(data.step || 'Processing...', 'info');
            break;

        case 'agents_designed':
            if (data.agents) {
                data.agents.forEach(agent => {
                    addAgent(agent.name, agent.tool || guessToolFromName(agent.name), 'pending');
                });
                renderDAG(data.agents);
                addLog(`${data.agents.length} agents designed`, 'agent');
            }
            break;

        case 'agent_executing':
            updateAgentStatus(data.agent, 'running');
            addLog(`Agent "${data.agent}" started`, 'agent');
            break;

        case 'agent_completed':
            const result = data.result || {};
            updateAgentStatus(result.agent, result.status || 'completed');
            addLog(`Agent "${result.agent}" completed: ${(result.summary || '').slice(0, 100)}`, 'success');
            break;

        case 'memory_retrieved':
            addLog(`Memory context retrieved (${(data.context || []).length} entries)`, 'info');
            break;

        case 'dialogue_completed':
            addLog(`Multi-agent dialogues completed (${(data.dialogues || []).length} conversations)`, 'info');
            break;

        case 'feedback_evaluated':
            addLog('Feedback evaluation complete', 'info');
            break;

        case 'ctde_trained':
            addLog(`CTDE trained — ${(data.policies_updated || []).length} policies updated`, 'info');
            break;

        case 'dependency_resolved':
            addLog(`Execution order: ${(data.order || []).join(' → ')}`, 'info');
            break;

        case 'orchestration_completed':
            addLog('✅ Orchestration pipeline completed', 'success');
            break;

        case 'final_output':
            showOutput(data);
            break;

        case 'error':
            addLog(`❌ Error: ${data.message}`, 'error');
            showToast('Workflow error: ' + data.message, 'error');
            break;

        case 'keepalive':
            break;

        default:
            addLog(`[${eventType}] ${JSON.stringify(data).slice(0, 100)}`, 'info');
    }
}

function onWorkflowComplete(isError) {
    const runBtn = document.getElementById('runBtn');
    runBtn.disabled = false;
    runBtn.innerHTML = 'Run Workflow';

    document.getElementById('logStatus').innerHTML = isError
        ? '<span class="badge badge-error"><span class="badge-dot"></span> Error</span>'
        : '<span class="badge badge-completed"><span class="badge-dot"></span> Complete</span>';
}

// =========================================
// AGENT CARDS
// =========================================

function addAgent(name, tool, status) {
    // Prevent duplicates
    if (agents.find(a => a.name === name)) return;
    agents.push({ name, tool, status });

    const list = document.getElementById('agentList');
    const card = document.createElement('div');
    card.className = `agent-card ${status}`;
    card.id = `agent-${sanitizeId(name)}`;
    card.innerHTML = `
        <div class="agent-status-dot ${status}"></div>
        <span class="agent-name">${name}</span>
        ${tool ? `<span class="agent-tool">${tool}</span>` : ''}
    `;
    list.appendChild(card);
    document.getElementById('agentCount').textContent = `${agents.length} agents`;
}

function updateAgentStatus(name, status) {
    const agent = agents.find(a => a.name === name);
    if (agent) agent.status = status;

    const card = document.getElementById(`agent-${sanitizeId(name)}`);
    if (card) {
        card.className = `agent-card ${status}`;
        const dot = card.querySelector('.agent-status-dot');
        if (dot) dot.className = `agent-status-dot ${status}`;
    }

    // Update DAG node
    const node = document.getElementById(`dag-node-${sanitizeId(name)}`);
    if (node) {
        const colors = { pending: '#555e72', running: '#3b82f6', completed: '#10b981', failed: '#ef4444' };
        node.setAttribute('fill', colors[status] || '#555e72');
    }
}

function guessToolFromName(name) {
    const n = name.toLowerCase();
    if (n.includes('csv') || n.includes('data') || n.includes('analy')) return 'csv_tool';
    if (n.includes('email') && n.includes('read')) return 'email_reader';
    if (n.includes('email') || n.includes('notif')) return 'email_tool';
    if (n.includes('slack')) return 'slack_tool';
    if (n.includes('zoom') || n.includes('video')) return 'zoom_tool';
    if (n.includes('calendar') || n.includes('schedule') || n.includes('meeting')) return 'calendar_tool';
    if (n.includes('sql') || n.includes('query')) return 'sql_tool';
    return null;
}

// =========================================
// DAG VISUALIZATION
// =========================================

function renderDAG(agentConfigs) {
    const svg = document.getElementById('dagSvg');
    if (!svg || !agentConfigs.length) return;

    const width = svg.clientWidth || 500;
    const nodeRadius = 28;
    const padding = 60;

    // Build dependency graph levels
    const agentMap = {};
    agentConfigs.forEach(a => { agentMap[a.name] = a; });

    const levels = [];
    const placed = new Set();
    let remaining = [...agentConfigs];

    while (remaining.length > 0) {
        const level = remaining.filter(a =>
            (a.dependencies || []).every(d => placed.has(d))
        );
        if (level.length === 0) {
            level.push(...remaining);
            remaining = [];
        } else {
            remaining = remaining.filter(a => !level.includes(a));
        }
        level.forEach(a => placed.add(a.name));
        levels.push(level);
    }

    const totalHeight = levels.length * 80 + padding;
    svg.setAttribute('height', totalHeight);

    let svgHTML = '';
    const nodePositions = {};

    // Draw nodes
    levels.forEach((level, li) => {
        const y = li * 80 + 50;
        const step = width / (level.length + 1);

        level.forEach((agent, ai) => {
            const x = step * (ai + 1);
            nodePositions[agent.name] = { x, y };

            // Node circle
            svgHTML += `
                <circle id="dag-node-${sanitizeId(agent.name)}" cx="${x}" cy="${y}" r="${nodeRadius}"
                    fill="#555e72" stroke="rgba(79,124,255,0.3)" stroke-width="2" class="dag-node"/>
                <text x="${x}" y="${y + 4}" text-anchor="middle" fill="white" font-size="9" font-weight="600" font-family="Inter">
                    ${agent.name.length > 10 ? agent.name.slice(0, 10) + '..' : agent.name}
                </text>
            `;
        });
    });

    // Draw edges
    agentConfigs.forEach(agent => {
        (agent.dependencies || []).forEach(dep => {
            const from = nodePositions[dep];
            const to = nodePositions[agent.name];
            if (from && to) {
                svgHTML = `
                    <line x1="${from.x}" y1="${from.y + nodeRadius}" x2="${to.x}" y2="${to.y - nodeRadius}"
                        stroke="rgba(79,124,255,0.3)" stroke-width="2" marker-end="url(#arrow)"/>
                ` + svgHTML;
            }
        });
    });

    // Arrow marker
    const defs = `
        <defs>
            <marker id="arrow" markerWidth="8" markerHeight="8" refX="8" refY="4" orient="auto">
                <path d="M 0 0 L 8 4 L 0 8 z" fill="rgba(79,124,255,0.5)"/>
            </marker>
        </defs>
    `;

    svg.innerHTML = defs + svgHTML;
}

// =========================================
// LIVE LOGS
// =========================================

function addLog(message, level = 'info') {
    const terminal = document.getElementById('logsTerminal');
    const entry = document.createElement('div');
    entry.className = `log-entry ${level}`;
    entry.innerHTML = `<span class="timestamp">[${formatTime()}]</span><span class="message">${message}</span>`;
    terminal.appendChild(entry);
    terminal.scrollTop = terminal.scrollHeight;
}

// =========================================
// FINAL OUTPUT — REPORT DISPLAY
// =========================================

let lastWorkflowOutput = null;

function showOutput(data) {
    const panel = document.getElementById('reportPanel');
    panel.style.display = 'block';

    const result = data.result || data;
    lastWorkflowOutput = result;

    // ── 1. Extract report, analysis, and summaries from agent results ──
    let reportText = null;
    let csvAnalysis = null;
    let outputFile = null;
    let llmSummary = null;
    let fileInfo = null;
    let agentSummaries = [];

    const results = result.results || [];
    for (const r of results) {
        const tr = r.tool_result || {};
        if (tr.report) reportText = tr.report;
        if (tr.analysis) csvAnalysis = tr.analysis;
        if (tr.output_file) outputFile = tr.output_file;
        if (tr.summary) llmSummary = tr.summary;  // data_summarizer_tool
        if (tr.file_info) fileInfo = tr.file_info;  // data_summarizer_tool
        // Collect agent reasoning summaries as fallback
        if (r.summary) agentSummaries.push({ agent: r.agent, summary: r.summary });
    }

    // ── 2. Analysis Summary Cards ──
    if (csvAnalysis) {
        const summaryEl = document.getElementById('analysisSummary');
        summaryEl.style.display = 'grid';
        summaryEl.innerHTML = buildAnalysisCards(csvAnalysis);
    }

    // Show file info cards if we have them from data_summarizer_tool
    if (fileInfo && !csvAnalysis) {
        const summaryEl = document.getElementById('analysisSummary');
        summaryEl.style.display = 'grid';
        let cards = [];
        if (fileInfo.name) cards.push(metricCard('📄', 'File', fileInfo.name));
        if (fileInfo.format) cards.push(metricCard('📋', 'Format', fileInfo.format));
        if (fileInfo.rows != null) cards.push(metricCard('📊', 'Rows', fileInfo.rows.toLocaleString()));
        if (fileInfo.cols != null) cards.push(metricCard('🔢', 'Columns', fileInfo.cols));
        summaryEl.innerHTML = cards.join('');
    }

    // ── 3. Report / LLM Summary / Fallback ──
    const card = document.getElementById('reportCard');
    const textEl = document.getElementById('reportText');
    card.style.display = 'block';

    if (llmSummary) {
        // LLM summary from data_summarizer_tool — render with rich formatting
        document.querySelector('#reportCard .card-title').textContent = '📊 AI-Generated Summary';
        textEl.innerHTML = renderMarkdown(llmSummary);
    } else if (reportText) {
        document.querySelector('#reportCard .card-title').textContent = '📊 Analysis Report';
        textEl.textContent = reportText;
    } else if (agentSummaries.length > 0) {
        // Fallback: show agent reasoning summaries
        document.querySelector('#reportCard .card-title').textContent = '📊 Workflow Results';
        const lines = ['═'.repeat(50), '  WORKFLOW RESULTS', '═'.repeat(50), ''];
        for (const s of agentSummaries) {
            lines.push(`  🤖 ${s.agent}`);
            lines.push(`  ${s.summary}`);
            lines.push('');
        }
        lines.push('─'.repeat(50));
        lines.push('  STATUS: COMPLETED ✅');
        lines.push('─'.repeat(50));
        textEl.textContent = lines.join('\n');
    } else {
        textEl.textContent = 'Workflow completed. No detailed output available.';
    }

    // ── 4. Raw JSON (collapsible) ──
    const rawCard = document.getElementById('rawOutputCard');
    rawCard.style.display = 'block';
    document.getElementById('outputContent').textContent = JSON.stringify(result, null, 2);
}

function buildAnalysisCards(analysis) {
    const cards = [];

    cards.push(metricCard('📄', 'Total Rows', (analysis.total_rows || 0).toLocaleString()));
    cards.push(metricCard('📊', 'Columns', analysis.total_columns || 0));
    cards.push(metricCard('⚠️', 'Missing Values', (analysis.missing_values || 0).toLocaleString(),
        analysis.missing_pct ? `${analysis.missing_pct}%` : null));
    cards.push(metricCard('🔁', 'Duplicates', (analysis.duplicate_rows || 0).toLocaleString()));

    const numCols = (analysis.numeric_columns || []).length;
    const catCols = (analysis.categorical_columns || []).length;
    const dtCols = (analysis.datetime_columns || []).length;
    cards.push(metricCard('🔢', 'Numeric', numCols));
    cards.push(metricCard('🏷️', 'Categorical', catCols));

    if (dtCols > 0) {
        cards.push(metricCard('📅', 'Datetime', dtCols));
    }

    // Highlight top numeric column
    const highlights = analysis.numeric_highlights || {};
    const firstCol = Object.keys(highlights)[0];
    if (firstCol) {
        const h = highlights[firstCol];
        cards.push(metricCard('📈', firstCol,
            `${fmtNum(h.min)} — ${fmtNum(h.max)}`,
            `mean: ${fmtNum(h.mean)}`));
    }

    return cards.join('');
}

function metricCard(icon, label, value, subtitle) {
    return `
        <div class="metric-card">
            <div class="metric-icon">${icon}</div>
            <div class="metric-content">
                <div class="metric-value">${value}</div>
                <div class="metric-label">${label}</div>
                ${subtitle ? `<div class="metric-sub">${subtitle}</div>` : ''}
            </div>
        </div>
    `;
}

function fmtNum(val) {
    if (val === null || val === undefined) return 'N/A';
    if (typeof val === 'number') {
        if (Math.abs(val) >= 1000000) return val.toLocaleString(undefined, {maximumFractionDigits: 0});
        if (Math.abs(val) >= 100) return val.toLocaleString(undefined, {maximumFractionDigits: 2});
        return val.toLocaleString(undefined, {maximumFractionDigits: 4});
    }
    return String(val);
}

function copyReport() {
    const reportText = document.getElementById('reportText')?.textContent || '';
    navigator.clipboard.writeText(reportText);
    showToast('Report copied to clipboard', 'success');
}

function copyOutput() {
    const content = document.getElementById('outputContent').textContent;
    navigator.clipboard.writeText(content);
    showToast('Output copied to clipboard', 'success');
}

async function saveToFiles() {
    const reportText = document.getElementById('reportText')?.textContent;
    if (!reportText) {
        showToast('No report to save', 'error');
        return;
    }

    try {
        const blob = new Blob([reportText], { type: 'text/plain' });
        const fileName = `report_${currentWorkflowId ? currentWorkflowId.slice(0, 8) : 'output'}_${Date.now()}.txt`;

        const formData = new FormData();
        formData.append('file', blob, fileName);

        await apiUpload('/files/upload', formData);
        showToast(`Report saved as "${fileName}" — check Files section`, 'success');
    } catch (err) {
        showToast('Failed to save report: ' + err.message, 'error');
    }
}

// =========================================
// HELPERS
// =========================================

function sanitizeId(name) {
    return name.replace(/[^a-zA-Z0-9]/g, '_');
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function renderMarkdown(text) {
    // Simple markdown → HTML for LLM output display
    let html = escapeHtml(text);

    // Headers: ### text → <strong>text</strong>
    html = html.replace(/^#{1,4}\s+(.+)$/gm, '<strong class="md-heading">$1</strong>');

    // Bold: **text** → <strong>text</strong>
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic: *text* → <em>text</em>
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Bullet points: - text → styled bullet
    html = html.replace(/^[-•]\s+(.+)$/gm, '<span class="md-bullet">• $1</span>');

    // Numbered lists: 1. text → styled number
    html = html.replace(/^(\d+)\.\s+(.+)$/gm, '<span class="md-bullet">$1. $2</span>');

    // Line breaks
    html = html.replace(/\n/g, '<br>');

    return html;
}
