/**
 * AutoOps AI — API Client Module
 *
 * Central API client with JWT header injection, toast notifications,
 * auth guard, and user widget initialization.
 */

const API_BASE = window.location.origin + '/api';

// ── Auth Token Management ──

function getToken() {
    return localStorage.getItem('autoops_token');
}

function getUser() {
    const raw = localStorage.getItem('autoops_user');
    return raw ? JSON.parse(raw) : null;
}

function setAuth(token, user) {
    localStorage.setItem('autoops_token', token);
    localStorage.setItem('autoops_user', JSON.stringify(user));
}

function clearAuth() {
    localStorage.removeItem('autoops_token');
    localStorage.removeItem('autoops_user');
}

function logout() {
    clearAuth();
    window.location.href = 'index.html';
}

// ── Auth Guard (call on protected pages) ──

function requireAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = 'index.html';
        return false;
    }
    initUserWidget();
    return true;
}

// ── User Widget in Sidebar ──

function initUserWidget() {
    const user = getUser();
    if (!user) return;

    const avatarEl = document.getElementById('userAvatar');
    const nameEl = document.getElementById('userName');
    const roleEl = document.getElementById('userRole');

    if (avatarEl) avatarEl.textContent = (user.full_name || 'U')[0].toUpperCase();
    if (nameEl) nameEl.textContent = user.full_name || 'User';
    if (roleEl) roleEl.textContent = user.role || 'employee';
}

// ── Fetch Wrapper with JWT ──

async function apiFetch(path, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    // Remove Content-Type for FormData
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        clearAuth();
        window.location.href = 'index.html';
        throw new Error('Unauthorized');
    }

    return response;
}

async function apiGet(path) {
    const res = await apiFetch(path);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Request failed');
    }
    return res.json();
}

async function apiPost(path, body) {
    const res = await apiFetch(path, {
        method: 'POST',
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Request failed');
    }
    return res.json();
}

async function apiDelete(path) {
    const res = await apiFetch(path, { method: 'DELETE' });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Request failed');
    }
    return res.json();
}

async function apiUpload(path, formData) {
    const token = getToken();
    const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
}

// ── Toast Notifications ──

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="message">${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(30px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ── Utility: Format Date ──

function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function formatTime() {
    return new Date().toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    });
}

// ── Status Badge HTML ──

function statusBadge(status) {
    const s = (status || 'pending').toLowerCase();
    return `<span class="badge badge-${s}"><span class="badge-dot"></span> ${s}</span>`;
}
