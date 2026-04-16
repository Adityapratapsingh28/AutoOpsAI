import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = 'http://127.0.0.1:8000/api';

const cardStyle = {
    background: '#ffffff',
    borderRadius: '20px',
    boxShadow: 'rgba(0,0,0,0.02) 0px 0px 0px 1px, rgba(0,0,0,0.04) 0px 2px 6px, rgba(0,0,0,0.1) 0px 4px 8px',
    color: '#222222',
    overflow: 'hidden'
};

export default function ManagerLogs() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const token = localStorage.getItem('autoops_token');
                if (!token) return navigate('/');

                const res = await fetch(`${API_BASE}/manager/logs`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (res.ok) {
                    setLogs(await res.json());
                }
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchLogs();
    }, [navigate]);

    if (loading) return <div style={{ padding: '2rem', color: '#222222' }}>Loading logs...</div>;

    return (
        <div style={{ padding: '24px', fontFamily: '"Airbnb Cereal VF", Circular, -apple-system, sans-serif' }}>
            <div style={{ marginBottom: '32px' }}>
                <h1 style={{ fontSize: '28px', fontWeight: '700', color: '#222222', letterSpacing: '-0.44px', marginBottom: '8px' }}>
                    Audit & System Logs
                </h1>
                <p style={{ fontSize: '16px', color: '#6a6a6a', margin: 0 }}>
                    Monitor agent behaviors, errors, and system health
                </p>
            </div>

            <div style={{ ...cardStyle }}>
                <div style={{ padding: '24px', borderBottom: '1px solid #c1c1c1', background: '#fafafa' }}>
                    <h2 style={{ fontSize: '20px', fontWeight: '600', margin: 0 }}>System Event Stream</h2>
                </div>
                
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontFamily: 'ui-monospace, Menlo, Monaco, "Courier New", monospace', fontSize: '13px' }}>
                        <thead>
                            <tr style={{ background: '#ffffff' }}>
                                <th style={{ padding: '16px 24px', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontWeight: '600' }}>Timestamp</th>
                                <th style={{ padding: '16px 24px', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontWeight: '600' }}>Level</th>
                                <th style={{ padding: '16px 24px', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontWeight: '600' }}>Source / Agent</th>
                                <th style={{ padding: '16px 24px', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontWeight: '600' }}>Message</th>
                            </tr>
                        </thead>
                        <tbody>
                            {logs.length === 0 ? (
                                <tr>
                                    <td colSpan="4" style={{ padding: '24px', textAlign: 'center', color: '#6a6a6a', fontFamily: 'inherit' }}>No logs generated yet.</td>
                                </tr>
                            ) : logs.map(log => {
                                const levelColor = {
                                    info: '#3f3f3f',
                                    warning: '#b45309', // amber/orange
                                    error: '#c13515',   // red
                                    debug: '#428bff'    // blue
                                }[log.level?.toLowerCase()] || '#3f3f3f';
                                
                                return (
                                    <tr key={log.id} style={{ borderBottom: '1px solid #f2f2f2' }}>
                                        <td style={{ padding: '12px 24px', color: '#929292', whiteSpace: 'nowrap' }}>
                                            {new Date(log.created_at).toLocaleString()}
                                        </td>
                                        <td style={{ padding: '12px 24px' }}>
                                            <span style={{ 
                                                color: levelColor, 
                                                background: `${levelColor}15`, 
                                                padding: '2px 8px', 
                                                borderRadius: '4px', 
                                                fontWeight: '600',
                                                textTransform: 'uppercase',
                                                fontSize: '11px'
                                            }}>
                                                {log.level}
                                            </span>
                                        </td>
                                        <td style={{ padding: '12px 24px', color: '#222222', fontWeight: '500' }}>
                                            {log.source || 'SYSTEM'}
                                        </td>
                                        <td style={{ padding: '12px 24px', color: '#3f3f3f', maxWidth: '400px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={log.message}>
                                            {log.message}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
