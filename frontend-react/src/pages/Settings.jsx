import React, { useState, useEffect } from 'react';

export default function Settings() {
    const [user, setUser] = useState({});

    useEffect(() => {
        const stored = localStorage.getItem('autoops_user');
        if (stored) setUser(JSON.parse(stored));
    }, []);

    return (
        <React.Fragment>
            <div className="page-header">
                <h1>⚙️ Settings</h1>
                <p>Manage your profile and application preferences.</p>
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
        </React.Fragment>
    );
}
