import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

const API_BASE = '/api';

export default function Dashboard() {
    const cache = JSON.parse(sessionStorage.getItem('dashboard_cache') || 'null');
    
    const [stats, setStats] = useState(cache ? cache.stats : { total_workflows: '—', completed: '—', running: '—', files: '—', success_rate: '—' });
    const [recentWorkflows, setRecentWorkflows] = useState(cache ? cache.recentWorkflows : []);
    const [loading, setLoading] = useState(!cache);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        let isMounted = true;
        const fetchDashboard = async () => {
            try {
                const token = localStorage.getItem('autoops_token');
                if (!token) {
                    navigate('/');
                    return;
                }

                const res = await fetch(`${API_BASE}/dashboard`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (res.status === 401) {
                    localStorage.removeItem('autoops_token');
                    navigate('/');
                    return;
                }

                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Failed');

                if (isMounted) {
                    setStats(data.stats);
                    setRecentWorkflows(data.recent_workflows);
                    sessionStorage.setItem('dashboard_cache', JSON.stringify({ stats: data.stats, recentWorkflows: data.recent_workflows }));
                }
            } catch (err) {
                if (isMounted) setError(err.message);
            } finally {
                if (isMounted) setLoading(false);
            }
        };
        fetchDashboard();
        return () => { isMounted = false; };
    }, [navigate]);

    return (
        <React.Fragment>
            <div className="page-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <h1>Dashboard</h1>
                    {stats.served_from === 'redis' && (
                        <span style={{ background: 'linear-gradient(90deg, #ef4444, #f97316)', color: 'white', padding: '4px 12px', borderRadius: '20px', fontSize: '0.8rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '4px', boxShadow: '0 0 10px rgba(239, 68, 68, 0.4)' }}>
                            ⚡ Served from Redis Cache
                        </span>
                    )}
                </div>
                <p>Welcome back! Here's an overview of your workflow activity.</p>
            </div>

            <div className="stats-grid" id="statsGrid">
                <div className="stat-card">
                    <div className="stat-icon blue">📊</div>
                    <div className="stat-value">{stats.total_workflows}</div>
                    <div className="stat-label">Total Workflows</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon green">✅</div>
                    <div className="stat-value">{stats.completed}</div>
                    <div className="stat-label">Completed</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon amber">🔄</div>
                    <div className="stat-value">{stats.running}</div>
                    <div className="stat-label">Running</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon purple">📁</div>
                    <div className="stat-value">{stats.files}</div>
                    <div className="stat-label">Files Uploaded</div>
                </div>
                <div className="stat-card">
                    <div className="stat-icon green">📈</div>
                    <div className="stat-value">{stats.success_rate}{stats.success_rate !== '—' ? '%' : ''}</div>
                    <div className="stat-label">Success Rate</div>
                </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
                <Link to="/workflow" className="btn btn-primary">New Workflow</Link>
                <Link to="/files" className="btn btn-secondary">📁 Upload File</Link>
            </div>

            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">Recent Workflows</h3>
                    <Link to="/history" className="btn btn-ghost btn-sm">View All →</Link>
                </div>
                <div className="table-container">
                    {error && <p style={{ color: 'red', padding: '1rem' }}>{error}</p>}
                    <table>
                        <thead>
                            <tr>
                                <th>Input</th>
                                <th>Status</th>
                                <th>Date</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading && (
                                <tr>
                                    <td colSpan="4" className="text-center text-muted" style={{ padding: '2rem' }}>Loading...</td>
                                </tr>
                            )}
                            {!loading && recentWorkflows.length === 0 && (
                                <tr>
                                    <td colSpan="4" className="text-center text-muted" style={{ padding: '2rem' }}>
                                        No workflows yet. <Link to="/workflow" style={{ color: 'var(--accent-primary)' }}>Run your first one →</Link>
                                    </td>
                                </tr>
                            )}
                            {!loading && recentWorkflows.map(w => (
                                <tr key={w.id}>
                                    <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                        {w.input_text}
                                    </td>
                                    <td>
                                        <span className={`badge badge-${(w.status || 'pending').toLowerCase()}`}>
                                            <span className="badge-dot"></span> {(w.status || 'pending').toLowerCase()}
                                        </span>
                                    </td>
                                    <td className="text-muted text-sm">
                                        {new Date(w.created_at).toLocaleDateString()} {new Date(w.created_at).toLocaleTimeString()}
                                    </td>
                                    <td><Link to={`/workflow?id=${w.id}`} className="btn btn-ghost btn-sm">View</Link></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="card mt-2">
                <div className="card-header">
                    <h3 className="card-title">💡 Suggested Workflows</h3>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(250px,1fr))', gap: '0.75rem' }}>
                    <div className="card" style={{ cursor: 'pointer' }} onClick={() => navigate('/workflow?prompt=' + encodeURIComponent('Analyze CSV and notify team'))}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>📊 Analyze CSV & Notify</div>
                        <div className="text-sm text-muted mt-1">Parse uploaded data and email results to your team</div>
                    </div>
                    <div className="card" style={{ cursor: 'pointer' }} onClick={() => navigate('/workflow?prompt=' + encodeURIComponent('Schedule team meeting and send Slack notification'))}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>📅 Schedule & Notify</div>
                        <div className="text-sm text-muted mt-1">Create a meeting and alert your team on Slack</div>
                    </div>
                    <div className="card" style={{ cursor: 'pointer' }} onClick={() => navigate('/workflow?prompt=' + encodeURIComponent('Read latest emails and generate summary report'))}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>📧 Email Summary</div>
                        <div className="text-sm text-muted mt-1">Scan your inbox and create an actionable summary</div>
                    </div>
                </div>
            </div>
        </React.Fragment>
    );
}
