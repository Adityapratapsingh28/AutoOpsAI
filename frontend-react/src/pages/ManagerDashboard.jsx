import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

const API_BASE = 'http://127.0.0.1:8000/api';

const cardStyle = {
    background: '#ffffff',
    borderRadius: '20px',
    padding: '24px',
    boxShadow: 'rgba(0,0,0,0.02) 0px 0px 0px 1px, rgba(0,0,0,0.04) 0px 2px 6px, rgba(0,0,0,0.1) 0px 4px 8px',
    color: '#222222'
};

const buttonStyle = {
    background: '#ff385c',
    color: '#ffffff',
    padding: '12px 24px',
    borderRadius: '8px',
    fontWeight: '500',
    border: 'none',
    cursor: 'pointer',
    fontSize: '16px'
};

export default function ManagerDashboard() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchDashboard = async () => {
            try {
                const token = localStorage.getItem('autoops_token');
                if (!token) {
                    navigate('/');
                    return;
                }

                const res = await fetch(`${API_BASE}/manager/dashboard`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (res.status === 401 || res.status === 403) {
                    navigate('/');
                    return;
                }

                const json = await res.json();
                if (!res.ok) throw new Error(json.detail || 'Failed');
                setData(json);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchDashboard();
    }, [navigate]);

    if (loading) return <div style={{ padding: '2rem', color: '#222222' }}>Loading manager data...</div>;
    if (error) return <div style={{ padding: '2rem', color: '#c13515' }}>Error: {error}</div>;

    const stats = data?.stats || {};
    const activity = data?.activity || [];

    return (
        <div style={{ padding: '24px', fontFamily: '"Airbnb Cereal VF", Circular, -apple-system, sans-serif' }}>
            <div style={{ marginBottom: '32px' }}>
                <h1 style={{ fontSize: '28px', fontWeight: '700', color: '#222222', letterSpacing: '-0.44px', marginBottom: '8px' }}>
                    Organization Overview
                </h1>
                <p style={{ fontSize: '16px', color: '#6a6a6a', margin: 0 }}>
                    Monitor team productivity and AI performance
                </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px', marginBottom: '32px' }}>
                <div style={cardStyle}>
                    <div style={{ fontSize: '14px', color: '#6a6a6a', fontWeight: '600' }}>Total Workflows</div>
                    <div style={{ fontSize: '32px', fontWeight: '700', color: '#222222', marginTop: '8px' }}>{stats.total_workflows}</div>
                </div>
                <div style={cardStyle}>
                    <div style={{ fontSize: '14px', color: '#6a6a6a', fontWeight: '600' }}>Success Rate</div>
                    <div style={{ fontSize: '32px', fontWeight: '700', color: '#222222', marginTop: '8px' }}>{stats.success_rate}%</div>
                </div>
                <div style={cardStyle}>
                    <div style={{ fontSize: '14px', color: '#6a6a6a', fontWeight: '600' }}>Failed Executions</div>
                    <div style={{ fontSize: '32px', fontWeight: '700', color: '#c13515', marginTop: '8px' }}>{stats.failed}</div>
                </div>
                <div style={cardStyle}>
                    <div style={{ fontSize: '14px', color: '#6a6a6a', fontWeight: '600' }}>Hours Saved (est.)</div>
                    <div style={{ fontSize: '32px', fontWeight: '700', color: '#ff385c', marginTop: '8px' }}>{stats.hours_saved}</div>
                </div>
            </div>

            <div style={{ ...cardStyle, padding: '0' }}>
                <div style={{ padding: '24px', borderBottom: '1px solid #c1c1c1' }}>
                    <h2 style={{ fontSize: '22px', fontWeight: '600', color: '#222222', letterSpacing: '-0.44px', margin: 0 }}>
                        Recent Org Activity
                    </h2>
                </div>
                <div style={{ padding: '0 24px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                        <thead>
                            <tr>
                                <th style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontSize: '13px', fontWeight: '600' }}>Employee</th>
                                <th style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontSize: '13px', fontWeight: '600' }}>Workflow</th>
                                <th style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontSize: '13px', fontWeight: '600' }}>Status</th>
                                <th style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontSize: '13px', fontWeight: '600' }}>Date</th>
                            </tr>
                        </thead>
                        <tbody>
                            {activity.length === 0 ? (
                                <tr>
                                    <td colSpan="4" style={{ padding: '24px 0', textAlign: 'center', color: '#6a6a6a' }}>No recent activity.</td>
                                </tr>
                            ) : activity.map(act => (
                                <tr key={act.id}>
                                    <td style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', fontSize: '14px', fontWeight: '500', color: '#222222' }}>{act.user_name}</td>
                                    <td style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', fontSize: '14px', color: '#6a6a6a', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{act.input_text}</td>
                                    <td style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8' }}>
                                        <span style={{ 
                                            background: act.status === 'completed' ? '#f0fdf4' : act.status === 'failed' ? '#fef2f2' : '#f0f4ff', 
                                            color: act.status === 'completed' ? '#166534' : act.status === 'failed' ? '#991b1b' : '#1e40af',
                                            padding: '4px 12px', borderRadius: '14px', fontSize: '11px', fontWeight: '600', textTransform: 'uppercase'
                                        }}>
                                            {act.status}
                                        </span>
                                    </td>
                                    <td style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', fontSize: '13px', color: '#6a6a6a' }}>
                                        {new Date(act.created_at).toLocaleDateString()}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
