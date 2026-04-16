import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function SignIn() {
    const [tab, setTab] = useState('login');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    // Login Form State
    const [loginEmail, setLoginEmail] = useState('');
    const [loginPassword, setLoginPassword] = useState('');

    // Signup Form State
    const [signupName, setSignupName] = useState('');
    const [signupEmail, setSignupEmail] = useState('');
    const [signupPassword, setSignupPassword] = useState('');
    const [signupRole, setSignupRole] = useState('employee');

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: loginEmail, password: loginPassword })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Login failed');

            localStorage.setItem('autoops_token', data.access_token);
            localStorage.setItem('autoops_user', JSON.stringify({
                user_id: data.user_id,
                role: data.role,
                full_name: data.full_name,
            }));
            navigate('/dashboard');
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleSignup = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/auth/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    full_name: signupName,
                    email: signupEmail,
                    password: signupPassword,
                    role: signupRole
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Signup failed');

            localStorage.setItem('autoops_token', data.access_token);
            localStorage.setItem('autoops_user', JSON.stringify({
                user_id: data.user_id,
                role: data.role,
                full_name: data.full_name,
            }));
            navigate('/dashboard');
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <React.Fragment>
            <div className="auth-container">
                <div className="auth-card">
                    <div className="auth-logo">
                        <h1>AUTOOPS AI</h1>
                        <p>Enterprise AI Workflow Automation</p>
                    </div>

                    {/* Tabs */}
                    <div className="auth-tabs">
                        <button 
                            className={`auth-tab ${tab === 'login' ? 'active' : ''}`} 
                            onClick={() => { setTab('login'); setError(null); }}
                        >Sign In</button>
                        <button 
                            className={`auth-tab ${tab === 'signup' ? 'active' : ''}`} 
                            onClick={() => { setTab('signup'); setError(null); }}
                        >Create Account</button>
                    </div>

                    {/* Login Form */}
                    {tab === 'login' && (
                        <form onSubmit={handleLogin}>
                            <div className="form-group">
                                <label htmlFor="loginEmail">Email Address</label>
                                <input type="email" id="loginEmail" className="form-input" placeholder="you@company.com" required 
                                    value={loginEmail} onChange={e => setLoginEmail(e.target.value)} />
                            </div>
                            <div className="form-group">
                                <label htmlFor="loginPassword">Password</label>
                                <input type="password" id="loginPassword" className="form-input" placeholder="Enter your password" required 
                                    value={loginPassword} onChange={e => setLoginPassword(e.target.value)} />
                            </div>
                            <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={loading}>
                                {loading ? 'Signing in...' : 'Sign In'}
                            </button>
                        </form>
                    )}

                    {/* Signup Form */}
                    {tab === 'signup' && (
                        <form onSubmit={handleSignup}>
                            <div className="form-group">
                                <label htmlFor="signupName">Full Name</label>
                                <input type="text" id="signupName" className="form-input" placeholder="John Doe" required 
                                    value={signupName} onChange={e => setSignupName(e.target.value)} />
                            </div>
                            <div className="form-group">
                                <label htmlFor="signupEmail">Email Address</label>
                                <input type="email" id="signupEmail" className="form-input" placeholder="you@company.com" required 
                                    value={signupEmail} onChange={e => setSignupEmail(e.target.value)} />
                            </div>
                            <div className="form-group">
                                <label htmlFor="signupPassword">Password</label>
                                <input type="password" id="signupPassword" className="form-input" placeholder="Min 6 characters" required minLength={6} 
                                    value={signupPassword} onChange={e => setSignupPassword(e.target.value)} />
                            </div>
                            <div className="form-group">
                                <label htmlFor="signupRole">Role</label>
                                <select id="signupRole" className="form-input" value={signupRole} onChange={e => setSignupRole(e.target.value)}>
                                    <option value="employee">Employee</option>
                                    <option value="manager">Manager</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                            <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={loading}>
                                {loading ? 'Creating account...' : 'Create Account'}
                            </button>
                        </form>
                    )}

                    {error && (
                        <p className="text-center text-sm mt-2" style={{ color: 'var(--error)' }}>
                            {error}
                        </p>
                    )}
                </div>
            </div>
            <div className="toast-container" id="toastContainer"></div>
        </React.Fragment>
    );
}
