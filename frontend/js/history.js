/**
 * AutoOps AI — Workflow History Page Logic
 */

if (!requireAuth()) throw new Error('Not authenticated');

let selectedWorkflowId = null;

async function loadHistory() {
    try {
        const data = await apiGet('/workflow/history');
        const tbody = document.getElementById('historyTable');

        if (!data.workflows || data.workflows.length === 0) {
            tbody.innerHTML = `
                <tr><td colspan="5" class="text-center text-muted" style="padding:2rem;">
                    No workflows yet. <a href="workflow.html" style="color:var(--accent-primary);">Run one →</a>
                </td></tr>`;
            return;
        }

        tbody.innerHTML = data.workflows.map(w => `
            <tr>
                <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${w.input_text}</td>
                <td>${w.agent_count || 0}</td>
                <td>${statusBadge(w.status)}</td>
                <td class="text-muted text-sm">${formatDate(w.created_at)}</td>
                <td>
                    <button class="btn btn-ghost btn-sm" onclick="viewDetail('${w.id}')">View</button>
                </td>
            </tr>
        `).join('');

    } catch (err) {
        showToast('Failed to load history: ' + err.message, 'error');
    }
}

async function viewDetail(id) {
    selectedWorkflowId = id;
    try {
        const data = await apiGet(`/workflow/${id}`);
        const modal = document.getElementById('detailModal');
        const content = document.getElementById('modalContent');
        const title = document.getElementById('modalTitle');

        title.textContent = data.workflow.input_text.slice(0, 60);

        let html = `<div style="margin-bottom:1rem;">${statusBadge(data.workflow.status)}</div>`;

        // Agents
        if (data.agents.length > 0) {
            html += `<h4 style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:0.5rem;">Agents (${data.agents.length})</h4>`;
            html += data.agents.map(a => `
                <div style="display:flex;align-items:center;gap:0.5rem;padding:0.4rem 0;font-size:0.82rem;">
                    <div class="agent-status-dot ${a.status}"></div>
                    <span>${a.name}</span>
                    ${a.tool ? `<span class="agent-tool">${a.tool}</span>` : ''}
                </div>
            `).join('');
        }

        // Logs (last 10)
        if (data.logs.length > 0) {
            html += `<h4 style="font-size:0.85rem;color:var(--text-secondary);margin:1rem 0 0.5rem;">Logs (${data.logs.length})</h4>`;
            html += `<div class="logs-terminal" style="max-height:150px;">`;
            data.logs.slice(-10).forEach(l => {
                html += `<div class="log-entry ${l.level}"><span class="message">${l.message}</span></div>`;
            });
            html += '</div>';
        }

        // Output
        if (data.output) {
            html += `<h4 style="font-size:0.85rem;color:var(--text-secondary);margin:1rem 0 0.5rem;">Output</h4>`;
            html += `<pre class="output-json" style="max-height:150px;overflow:auto;">${JSON.stringify(data.output.result, null, 2)}</pre>`;
        }

        content.innerHTML = html;
        modal.classList.remove('hidden');

    } catch (err) {
        showToast('Failed to load workflow: ' + err.message, 'error');
    }
}

function closeModal(e) {
    if (e.target.id === 'detailModal') {
        e.target.classList.add('hidden');
    }
}

function rerunWorkflow() {
    if (!selectedWorkflowId) return;
    document.getElementById('detailModal').classList.add('hidden');
    // Navigate to workflow page — the detail page will need to load input
    window.location.href = `workflow.html`;
}

loadHistory();
