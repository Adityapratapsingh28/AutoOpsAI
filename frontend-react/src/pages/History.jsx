import React, { useState, useEffect } from 'react';

const API_BASE = '/api';

export default function History() {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedWorkflow, setSelectedWorkflow] = useState(null);
    const [modalLoading, setModalLoading] = useState(false);

    const viewDetail = async (id) => {
        setModalLoading(true);
        setSelectedWorkflow({ id }); // open modal with loading state
        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch(`${API_BASE}/workflow/${id}`, { headers: { 'Authorization': `Bearer ${token}` } });
            const data = await res.json();
            if (res.ok) setSelectedWorkflow(data);
        } catch (err) {
            console.error(err);
        } finally {
            setModalLoading(false);
        }
    };

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const token = localStorage.getItem('autoops_token');
                if (!token) return;
                const res = await fetch(`${API_BASE}/workflow/history?limit=50`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const data = await res.json();
                if (res.ok) {
                    const arr = Array.isArray(data) ? data : (data.workflows || data.history || data.data || data.items || []);
                    setHistory(arr);
                }
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchHistory();
    }, []);

    return (
        <React.Fragment>
            <div className="page-header">
                <h1>📋 Workflow History</h1>
                <p>View your past workflow runs, statuses, and outputs.</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">All Workflows</h3>
                </div>
                <div className="table-container">
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
                            {loading && <tr><td colSpan="4" style={{ textAlign: 'center', padding: '2rem' }}>Loading...</td></tr>}
                            {!loading && history.length === 0 && <tr><td colSpan="4" style={{ textAlign: 'center', padding: '2rem' }}>No workflows found.</td></tr>}
                            {!loading && history.map(w => (
                                <tr key={w.id}>
                                    <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{w.input_text}</td>
                                    <td>
                                        <span className={`badge badge-${(w.status || 'pending').toLowerCase()}`}>
                                            <span className="badge-dot"></span> {(w.status || 'pending').toLowerCase()}
                                        </span>
                                    </td>
                                    <td className="text-muted text-sm">{new Date(w.created_at).toLocaleDateString()} {new Date(w.created_at).toLocaleTimeString()}</td>
                                    <td><button onClick={() => viewDetail(w.id)} className="btn btn-ghost btn-sm">View</button></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {selectedWorkflow && (
                <div className="modal-overlay" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 100 }}>
                    <div className="modal card" style={{ display: 'flex', flexDirection: 'column', margin: '5vh auto', width: '90%', maxWidth: '800px', maxHeight: '90vh', background: 'var(--bg-card)', padding: '2rem', overflowY: 'auto' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                            <h3 className="card-title">
                                {selectedWorkflow.workflow ? selectedWorkflow.workflow.input_text : 'Loading...'}
                            </h3>
                            <button className="btn btn-ghost" onClick={() => setSelectedWorkflow(null)}>✕</button>
                        </div>
                        
                        {modalLoading ? <p>Loading details...</p> : selectedWorkflow.workflow ? (
                            <div>
                                <div style={{ marginBottom: '1.5rem' }}>
                                    <span className={`badge badge-${selectedWorkflow.workflow.status.toLowerCase()}`}>
                                        <span className="badge-dot"></span> {selectedWorkflow.workflow.status}
                                    </span>
                                </div>
                                
                                {selectedWorkflow.agents && selectedWorkflow.agents.length > 0 && (
                                    <div style={{ marginBottom: '1.5rem' }}>
                                        <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Agents ({selectedWorkflow.agents.length})</h4>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                            {selectedWorkflow.agents.map((a, i) => (
                                                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem' }}>
                                                    <div className={`agent-status-dot ${a.status.toLowerCase()}`}></div>
                                                    <span>{a.name}</span>
                                                    {a.tool && <span className="agent-tool" style={{ background: 'var(--bg-secondary)', padding: '2px 6px', borderRadius: '4px' }}>{a.tool}</span>}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                
                                {selectedWorkflow.logs && selectedWorkflow.logs.length > 0 && (
                                    <div style={{ marginBottom: '1.5rem' }}>
                                        <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Logs (Last 10)</h4>
                                        <div className="logs-terminal" style={{ background: '#1e1e1e', padding: '1rem', borderRadius: '4px', maxHeight: '200px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '13px' }}>
                                            {selectedWorkflow.logs.slice(-10).map((l, i) => (
                                                <div key={i} style={{ marginBottom: '4px', color: l.level === 'error' ? 'var(--error)' : '#00ff00' }}>
                                                    <span className="message">{l.message}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {selectedWorkflow.output && selectedWorkflow.output.result && (
                                    <div>
                                        <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Output</h4>
                                        <pre className="output-json" style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '4px', maxHeight: '250px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                                            {typeof selectedWorkflow.output.result === 'string' ? selectedWorkflow.output.result : JSON.stringify(selectedWorkflow.output.result, null, 2)}
                                        </pre>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <p style={{ color: 'var(--error)' }}>Failed to load workflow details.</p>
                        )}
                    </div>
                </div>
            )}
        </React.Fragment>
    );
}
