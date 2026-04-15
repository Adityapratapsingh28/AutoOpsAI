/**
 * AutoOps AI — Auth Page Logic
 *
 * Handles login/signup form switching, form submission,
 * and redirect to dashboard on success.
 */

// Redirect if already logged in
(function checkAuth() {
    if (getToken() && getUser()) {
        window.location.href = 'dashboard.html';
    }
})();

// ── Tab Switching ──

function switchTab(tab) {
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    const loginTab = document.getElementById('loginTab');
    const signupTab = document.getElementById('signupTab');
    const authError = document.getElementById('authError');

    authError.classList.add('hidden');

    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        signupForm.classList.add('hidden');
        loginTab.classList.add('active');
        signupTab.classList.remove('active');
    } else {
        loginForm.classList.add('hidden');
        signupForm.classList.remove('hidden');
        loginTab.classList.remove('active');
        signupTab.classList.add('active');
    }
}

// ── Login ──

async function handleLogin(e) {
    e.preventDefault();
    const btn = document.getElementById('loginBtn');
    const authError = document.getElementById('authError');

    btn.disabled = true;
    btn.textContent = 'Signing in...';
    authError.classList.add('hidden');

    try {
        const data = await apiPost('/auth/login', {
            email: document.getElementById('loginEmail').value,
            password: document.getElementById('loginPassword').value,
        });

        setAuth(data.access_token, {
            user_id: data.user_id,
            role: data.role,
            full_name: data.full_name,
        });

        window.location.href = 'dashboard.html';
    } catch (err) {
        authError.textContent = err.message || 'Login failed';
        authError.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
}

// ── Signup ──

async function handleSignup(e) {
    e.preventDefault();
    const btn = document.getElementById('signupBtn');
    const authError = document.getElementById('authError');

    btn.disabled = true;
    btn.textContent = 'Creating account...';
    authError.classList.add('hidden');

    try {
        const data = await apiPost('/auth/signup', {
            full_name: document.getElementById('signupName').value,
            email: document.getElementById('signupEmail').value,
            password: document.getElementById('signupPassword').value,
            role: document.getElementById('signupRole').value,
        });

        setAuth(data.access_token, {
            user_id: data.user_id,
            role: data.role,
            full_name: data.full_name,
        });

        window.location.href = 'dashboard.html';
    } catch (err) {
        authError.textContent = err.message || 'Signup failed';
        authError.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Account';
    }
}
