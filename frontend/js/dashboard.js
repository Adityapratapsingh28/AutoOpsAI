/**
 * AutoOps AI — Dashboard Logic
 *
 * Loads stats, recent workflows, and handles suggestion clicks.
 */

// Auth guard
if (!requireAuth()) throw new Error('Not authenticated');

// ── Load Dashboard Data ──

async function loadDashboard() {
    try {
        const data = await apiGet('/dashboard');
        const s = data.stats;

        document.getElementById('statTotal').textContent = s.total_workflows;
        document.getElementById('statCompleted').textContent = s.completed;
        document.getElementById('statRunning').textContent = s.running;
        document.getElementById('statFiles').textContent = s.files;
        document.getElementById('statSuccess').textContent = s.success_rate + '%';

        // Recent workflows
        const tbody = document.getElementById('recentWorkflows');
        if (data.recent_workflows.length === 0) {
            tbody.innerHTML = `
                <tr><td colspan="4" class="text-center text-muted" style="padding:2rem;">
                    No workflows yet. <a href="workflow.html" style="color:var(--accent-primary);">Run your first one →</a>
                </td></tr>`;
        } else {
            tbody.innerHTML = data.recent_workflows.map(w => `
                <tr>
                    <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${w.input_text}</td>
                    <td>${statusBadge(w.status)}</td>
                    <td class="text-muted text-sm">${formatDate(w.created_at)}</td>
                    <td><a href="workflow.html?id=${w.id}" class="btn btn-ghost btn-sm">View</a></td>
                </tr>
            `).join('');
        }
    } catch (err) {
        showToast('Failed to load dashboard: ' + err.message, 'error');
    }
}

function runSuggestion(text) {
    window.location.href = `workflow.html?prompt=${encodeURIComponent(text)}`;
}

loadDashboard();
