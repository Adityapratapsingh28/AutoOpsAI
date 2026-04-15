// Theme Switcher Logic
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const nextTheme = current === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('theme', nextTheme);
    
    // Update button icon if exists
    const btn = document.getElementById('themeToggleBtn');
    if(btn) {
        btn.innerHTML = nextTheme === 'dark' ? '☀️' : '🌙';
    }
}

// Auto-apply on load
(function() {
    const saved = localStorage.getItem('theme') || 'light';
    if(saved === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
})();

// Once DOM is loaded, update button state
document.addEventListener('DOMContentLoaded', () => {
    const saved = localStorage.getItem('theme') || 'light';
    const btn = document.getElementById('themeToggleBtn');
    if(btn) {
        btn.innerHTML = saved === 'dark' ? '☀️' : '🌙';
    }
});
