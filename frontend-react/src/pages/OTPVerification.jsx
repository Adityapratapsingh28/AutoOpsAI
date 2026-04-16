import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function OTPVerification() {
    const [otp, setOtp] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const [resendStatus, setResendStatus] = useState(null);

    const navigate = useNavigate();
    const location = useLocation();
    const email = location.state?.email;

    if (!email) {
        // Direct route access without login
        navigate('/');
        return null;
    }

    const handleVerify = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResendStatus(null);
        
        try {
            const res = await fetch(`${API_BASE}/auth/verify-otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, otp })
            });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.detail || 'OTP Verification failed');

            // Store final verified token
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

    const handleResend = async () => {
        setLoading(true);
        setError(null);
        setResendStatus(null);
        try {
            const res = await fetch(`${API_BASE}/auth/resend-otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed to resend OTP');
            setResendStatus(data.message);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card" style={{ maxWidth: '450px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div className="auth-logo">
                    <h1>MFA Security</h1>
                    <p style={{ marginTop: '8px' }}>We sent a 6-digit verification code to<br /><strong>{email}</strong></p>
                </div>

                <form onSubmit={handleVerify} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div className="form-group" style={{ textAlign: 'center' }}>
                        <input 
                            type="text" 
                            className="form-input" 
                            placeholder="• • • • • •" 
                            required 
                            maxLength={6}
                            style={{ fontSize: '24px', letterSpacing: '8px', textAlign: 'center', padding: '16px' }}
                            value={otp} 
                            onChange={e => setOtp(e.target.value.replace(/[^0-9]/g, ''))} 
                        />
                    </div>
                    
                    <button type="submit" className="btn btn-primary btn-full btn-lg" disabled={loading || otp.length !== 6}>
                        {loading ? 'Verifying...' : 'Verify Secure Login'}
                    </button>
                </form>

                <div style={{ textAlign: 'center', marginTop: '8px' }}>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                        Didn't receive the code? 
                        <button 
                            onClick={handleResend}
                            disabled={loading}
                            style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', fontWeight: '600', cursor: 'pointer', marginLeft: '6px' }}
                        >
                            Resend Email
                        </button>
                    </p>
                </div>

                {error && (
                    <p className="text-center text-sm" style={{ color: 'var(--error)' }}>
                        {error}
                    </p>
                )}
                
                {resendStatus && (
                    <p className="text-center text-sm" style={{ color: 'var(--success)' }}>
                        {resendStatus}
                    </p>
                )}
            </div>
        </div>
    );
}
