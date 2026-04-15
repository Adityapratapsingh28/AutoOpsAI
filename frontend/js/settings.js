/**
 * AutoOps AI — Settings Page Logic
 */

if (!requireAuth()) throw new Error('Not authenticated');

async function loadProfile() {
    try {
        const profile = await apiGet('/auth/me');
        document.getElementById('settingsName').value = profile.full_name || '';
        document.getElementById('settingsEmail').value = profile.email || '';
        document.getElementById('settingsRole').value = profile.role || '';
        document.getElementById('settingsCreated').value = formatDate(profile.created_at);
    } catch (err) {
        showToast('Failed to load profile: ' + err.message, 'error');
    }
}

function saveProfile(e) {
    e.preventDefault();
    showToast('Profile updated (feature coming soon)', 'info');
}

loadProfile();
