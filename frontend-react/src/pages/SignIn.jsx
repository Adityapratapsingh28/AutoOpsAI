import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';

const API_BASE = '/api';

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
    const [signupConfirmPassword, setSignupConfirmPassword] = useState('');
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

            if (data.status === 'otp_required') {
                navigate('/verify-otp', { state: { email: data.email } });
                return;
            }

            localStorage.setItem('autoops_token', data.access_token);
            localStorage.setItem('autoops_user', JSON.stringify({
                user_id: data.user_id,
                role: data.role,
                full_name: data.full_name,
            }));
            if (data.role === 'manager' || data.role === 'admin') {
                navigate('/manager/dashboard');
            } else {
                navigate('/dashboard');
            }
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
        if (signupPassword !== signupConfirmPassword) {
            setError("Passwords do not match");
            setLoading(false);
            return;
        }
        
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

            if (data.status === 'success') {
                setTab('login');
                setLoginEmail(signupEmail);
                setError('Account created successfully! Please log in to complete verification.');
                return;
            }
            
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSuccess = async (credentialResponse) => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/auth/google`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ credential: credentialResponse.credential })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Google login failed');

            localStorage.setItem('autoops_token', data.access_token);
            localStorage.setItem('autoops_user', JSON.stringify({
                user_id: data.user_id,
                role: data.role,
                full_name: data.full_name,
            }));

            if (data.role === 'manager' || data.role === 'admin') {
                navigate('/manager/dashboard');
            } else {
                navigate('/dashboard');
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSignup = async (credentialResponse) => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/auth/google`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    credential: credentialResponse.credential,
                    role: signupRole  // Pass the selected role for new accounts
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Google signup failed');

            localStorage.setItem('autoops_token', data.access_token);
            localStorage.setItem('autoops_user', JSON.stringify({
                user_id: data.user_id,
                role: data.role,
                full_name: data.full_name,
            }));

            if (data.role === 'manager' || data.role === 'admin') {
                navigate('/manager/dashboard');
            } else {
                navigate('/dashboard');
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleError = () => {
        console.log("🔴 Google Login Failed");
        setError("Failed to authenticate with Google. Please try again.");
    };

    return (
        <React.Fragment>
            <div className="auth-container">
                <div className="auth-card">
                    <div className="auth-logo">
                        <h1>AUTOPS AI</h1>
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

                            <div style={{ display: 'flex', alignItems: 'center', margin: '20px 0', color: '#6a6a6a', fontSize: '13px' }}>
                                <div style={{ flex: 1, height: '1px', background: '#e8e8e8' }}></div>
                                <span style={{ padding: '0 10px' }}>OR CONTINUE WITH</span>
                                <div style={{ flex: 1, height: '1px', background: '#e8e8e8' }}></div>
                            </div>
                            
                            <div style={{ display: 'flex', justifyContent: 'center' }}>
                                <GoogleLogin
                                    onSuccess={handleGoogleSuccess}
                                    onError={handleGoogleError}
                                    theme="outline"
                                    size="large"
                                    width="100%"
                                />
                            </div>
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
                                <label htmlFor="signupConfirmPassword">Confirm Password</label>
                                <input type="password" id="signupConfirmPassword" className="form-input" placeholder="Confirm your password" required minLength={6} 
                                    value={signupConfirmPassword} onChange={e => setSignupConfirmPassword(e.target.value)} />
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

                            <div style={{ display: 'flex', alignItems: 'center', margin: '20px 0', color: '#6a6a6a', fontSize: '13px' }}>
                                <div style={{ flex: 1, height: '1px', background: '#e8e8e8' }}></div>
                                <span style={{ padding: '0 10px' }}>OR SIGN UP WITH</span>
                                <div style={{ flex: 1, height: '1px', background: '#e8e8e8' }}></div>
                            </div>
                            <p style={{ fontSize: '11px', color: '#6a6a6a', textAlign: 'center', marginTop: '-12px', marginBottom: '8px' }}>
                                Role "{signupRole}" will be assigned to your Google account
                            </p>
                            <div style={{ display: 'flex', justifyContent: 'center' }}>
                                <GoogleLogin
                                    onSuccess={handleGoogleSignup}
                                    onError={handleGoogleError}
                                    theme="outline"
                                    size="large"
                                    width="100%"
                                    text="signup_with"
                                />
                            </div>
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
