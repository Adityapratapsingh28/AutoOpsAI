import React, { useState, useEffect } from 'react';

export default function Settings() {
    const [user, setUser] = useState({});
    const [toast, setToast] = useState(null);

    useEffect(() => {
        const stored = localStorage.getItem('autoops_user');
        if (stored) setUser(JSON.parse(stored));
    }, []);

    const showToast = (message, type = 'error') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 4000);
    };

    const handleCrashTest = async () => {
        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch('http://127.0.0.1:8000/api/dev/crash', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            
            // Fast API global exception handler returns 500 error gracefully
            if (res.status === 500) {
                showToast(data.message || 'Internal System Error - Try again.', 'error');
            } else {
                showToast('Unexpected response format', 'warning');
            }
        } catch (error) {
            showToast('Network error during crash simulation', 'error');
        }
    };

    return (
        <React.Fragment>
            {toast && (
                <div style={{
                    position: 'fixed', top: '20px', right: '20px', 
                    padding: '1rem', borderRadius: '8px', 
                    background: toast.type === 'error' ? '#EF4444' : '#F59E0B', 
                    color: '#fff', zIndex: 1000,
                    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
                }}>
                    <strong>{toast.type === 'error' ? '🚫 Error:' : '⚠️ Warning:'}</strong> {toast.message}
                </div>
            )}
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1>⚙️ Settings</h1>
                    <p>Manage your profile and application preferences.</p>
                </div>
                <div style={{ padding: '0.5rem 1rem', background: '#10B98120', border: '1px solid #10B981', color: '#10B981', borderRadius: '20px', fontSize: '0.875rem', fontWeight: 600 }}>
                    🛡️ Global Error Guard: Online
                </div>
            </div>
            <div className="settings-section mt-2">
                <h3>👤 Profile Information</h3>
                <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', maxWidth: '600px' }}>
                    <div className="form-group" style={{ flex: 1 }}>
                        <label>Full Name</label>
                        <input type="text" className="form-input" value={user.full_name || 'Anonymous'} disabled style={{ width: '100%' }} />
                    </div>
                    <div className="form-group" style={{ flex: 1 }}>
                        <label>Role</label>
                        <input type="text" className="form-input" value={user.role || 'Member'} disabled style={{ width: '100%' }} />
                    </div>
                </div>
            </div>
            
            <div className="settings-section" style={{ marginTop: '2rem' }}>
                <h3>🔔 Notifications</h3>
                <p className="text-sm text-muted">All email and slack notifications are natively dispatched via orchestrator agents.</p>
            </div>

            <div className="settings-section" style={{ marginTop: '2rem', background: '#EF444410', borderLeft: '4px solid #EF4444', padding: '1.5rem', borderRadius: '4px' }}>
                <h3 style={{ color: '#EF4444', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    ⚠️ Developer Security Testing
                </h3>
                <p className="text-sm text-muted" style={{ marginBottom: '1rem' }}>
                    This tools tests the Global Exception Handler. It triggers a deliberate division by zero on the backend server. If the handler is working, the UI will degrade gracefully without exposing python tracebacks.
                </p>
                <button 
                    onClick={handleCrashTest}
                    style={{ background: '#EF4444', color: '#fff', border: 'none', padding: '0.75rem 1.5rem', borderRadius: '6px', cursor: 'pointer', fontWeight: 600 }}
                >
                    💥 Simulate Critical Crash
                </button>
            </div>
        </React.Fragment>
    );
}
