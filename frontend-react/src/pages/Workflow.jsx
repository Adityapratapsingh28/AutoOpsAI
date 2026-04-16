import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';

const API_BASE = 'http://127.0.0.1:8000/api';

function renderMarkdown(text) {
    if (!text) return '';
    let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    html = html.replace(/^#{1,4}\s+(.+)$/gm, '<strong class="md-heading" style="display:block;margin-top:8px;font-size:1.1em">$1</strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/^[-•]\s+(.+)$/gm, '<div class="md-bullet" style="margin-left:16px">• $1</div>');
    html = html.replace(/^(\d+)\.\s+(.+)$/gm, '<div class="md-bullet" style="margin-left:16px">$1. $2</div>');
    html = html.replace(/\n/g, '<br/>');
    return html;
}

const DAGGraph = ({ agentsConfig }) => {
    if (!agentsConfig || agentsConfig.length === 0) {
        return (
            <div className="dag-container" style={{ padding: '2rem', textAlign: 'center', background: 'var(--bg-secondary)', borderRadius: '8px', color: 'var(--text-muted)' }}>
                Waiting for agent orchestration planning...
            </div>
        );
    }

    const width = 800; // static base, svg scales responsive
    const nodeRadius = 30;
    const padding = 60;

    const agentMap = {};
    agentsConfig.forEach(a => { agentMap[a.name] = a; });

    const levels = [];
    const placed = new Set();
    let remaining = [...agentsConfig];

    while (remaining.length > 0) {
        const level = remaining.filter(a => (a.dependencies || []).every(d => placed.has(d)));
        if (level.length === 0) {
            level.push(...remaining);
            remaining = [];
        } else {
            remaining = remaining.filter(a => !level.includes(a));
        }
        level.forEach(a => placed.add(a.name));
        levels.push(level);
    }

    const totalHeight = levels.length * 90 + padding;
    const nodePositions = {};

    return (
        <div style={{ width: '100%', overflowX: 'auto', background: 'var(--bg-secondary)', borderRadius: '12px', padding: '1rem' }}>
            <svg viewBox={`0 0 ${width} ${totalHeight}`} style={{ width: '100%', minWidth: '600px', height: '100%' }}>
                <defs>
                    <marker id="arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(79,124,255,0.4)" />
                    </marker>
                </defs>
                
                {/* Calculate positions */}
                {levels.map((level, li) => {
                    const y = li * 90 + 50;
                    const step = width / (level.length + 1);
                    level.forEach((agent, ai) => {
                        const x = step * (ai + 1);
                        nodePositions[agent.name] = { x, y };
                    });
                    return null;
                })}

                {/* Edges */}
                {agentsConfig.map((agent) => (
                    (agent.dependencies || []).map(dep => {
                        const from = nodePositions[dep];
                        const to = nodePositions[agent.name];
                        if (from && to) {
                            return <line key={`${from.x}-${to.x}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="rgba(79,124,255,0.3)" strokeWidth="2.5" markerEnd="url(#arrow)" />
                        }
                        return null;
                    })
                ))}

                {/* Nodes */}
                {agentsConfig.map((agent) => {
                    const pos = nodePositions[agent.name];
                    if (!pos) return null;
                    const colors = { pending: '#555e72', running: '#3b82f6', completed: '#10b981', failed: '#ef4444' };
                    const fillColor = colors[agent.status?.toLowerCase()] || '#555e72';
                    return (
                        <g key={agent.name} transform={`translate(${pos.x}, ${pos.y})`}>
                            <circle r={nodeRadius} fill={fillColor} stroke="rgba(255,255,255,0.1)" strokeWidth="2" style={{ transition: 'fill 0.4s ease' }} />
                            <text y="4" textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="600" fontFamily="Inter" style={{ pointerEvents: 'none' }}>
                                {agent.name.length > 12 ? agent.name.slice(0, 10) + '..' : agent.name}
                            </text>
                        </g>
                    );
                })}
            </svg>
        </div>
    );
};


export default function Workflow() {
    const [searchParams] = useSearchParams();
    const [prompt, setPrompt] = useState(searchParams.get('prompt') || '');
    const [file, setFile] = useState(null);
    const [workflowId, setWorkflowId] = useState(searchParams.get('id') || null);
    
    const [status, setStatus] = useState('idle'); // idle, running, done, error
    const [logs, setLogs] = useState([]);
    const [agents, setAgents] = useState([]); // List of agent objects
    const [reportData, setReportData] = useState(null); // Full result payload

    const eventSourceRef = useRef(null);
    const logsEndRef = useRef(null);

    useEffect(() => {
        if (logsEndRef.current) logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    useEffect(() => {
        if (workflowId) connectSSE(workflowId);
        return () => {
            if (eventSourceRef.current) eventSourceRef.current.close();
        };
    }, [workflowId]);

    const formatTime = () => {
        const d = new Date();
        return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`;
    };

    const addLog = (msg, level = 'info') => {
        setLogs(prev => [...prev, { time: formatTime(), msg, level }]);
    };

    const guessToolFromName = (name) => {
        const n = String(name).toLowerCase();
        if (n.includes('csv') || n.includes('analy')) return 'csv_tool';
        if (n.includes('email')) return 'email_tool';
        if (n.includes('slack')) return 'slack_tool';
        if (n.includes('zoom') || n.includes('video')) return 'zoom_tool';
        if (n.includes('schedule') || n.includes('calendar')) return 'calendar_tool';
        return 'agent';
    };

    const connectSSE = (id) => {
        setStatus('running');
        setLogs([]);
        addLog(`Connecting to Stream Channel [${id.slice(0,8)}]...`, 'info');
        
        const url = `${API_BASE}/workflow/stream/${id}`;
        eventSourceRef.current = new EventSource(url);

        eventSourceRef.current.onmessage = (event) => {
            try {
                const payload = JSON.parse(event.data);
                const { event: eventType, data } = payload;

                if (eventType === 'start') {
                    addLog('🚀 Workflow Engine Initialized — Connection to AutoOps runtime established', 'success');
                } else if (eventType === 'status') {
                    addLog(data.step || 'Processing...', 'info');
                } else if (eventType === 'agents_designed') {
                    const parsedAgents = (data.agents || []).map(a => ({
                        ...a,
                        status: 'pending',
                        tool: a.tool || guessToolFromName(a.name)
                    }));
                    setAgents(parsedAgents);
                    const toolSummary = parsedAgents.map(a => `${a.name}→${a.tool || 'LLM'}`).join(' | ');
                    addLog(`📐 MetaOrchestrator designed ${parsedAgents.length} specialized agents for this pipeline`, 'info');
                    addLog(`🗺️  Agent→Tool map: ${toolSummary}`, 'info');
                    addLog(`🧬 CTDE policy injection: fetching role-specific governance rules from PostgreSQL ctde_policies table...`, 'info');
                    addLog(`⚡ Asynchronous agent communication channels open — agents will share results via shared context store`, 'info');
                } else if (eventType === 'agent_executing') {
                    setAgents(prev => prev.map(a => a.name === data.agent ? { ...a, status: 'running' } : a));
                    addLog(`🤖 [AGENT START] ${data.agent} — LLM context window primed, memory retrieved, executing task...`, 'info');
                } else if (eventType === 'agent_completed') {
                    const resultAgent = data.result?.agent || data.agent;
                    setAgents(prev => prev.map(a => a.name === resultAgent ? { ...a, status: data.result?.status || 'completed' } : a));
                    const summary = data.result?.summary;
                    addLog(`✅ [AGENT DONE] ${resultAgent} — task completed${summary ? ': ' + summary.slice(0, 120) + (summary.length > 120 ? '...' : '') : ''}`, 'success');
                } else if (eventType === 'tool_execution') {
                    addLog(`🔧 [TOOL DISPATCH] Routing to external API: ${data.tool_name} — preparing payload from agent output...`, 'warning');
                } else if (eventType === 'error') {
                    setStatus('error');
                    addLog(`💥 [FATAL ERROR] ${data.message}`, 'error');
                    eventSourceRef.current.close();
                } else if (eventType === 'done' || eventType === 'final_output' || eventType === 'orchestration_completed') {
                    if (data.result) {
                        setReportData(data.result);
                    } else if (data.data) {
                        setReportData(data.data);
                    } else {
                       if (Object.keys(data).length > 2) setReportData(data);
                    }
                    setStatus('done');
                    addLog('🏁 [PIPELINE COMPLETE] All agents executed, tool results compiled, CTDE training update persisted to PostgreSQL.', 'success');
                    addLog('✅ Workflow execution graph finalized — results available in report section below.', 'success');
                    eventSourceRef.current.close();
                } else {
                    if (typeof data === 'string') addLog(data, 'info');
                }
            } catch (err) { console.error('SSE Error:', err); }
        };

        eventSourceRef.current.onerror = () => {
            addLog('Stream disconnected from backend orchestrator.', 'error');
            setStatus('error');
            eventSourceRef.current.close();
        };
    };

    const runWorkflow = async () => {
        if (!prompt) return;
        setStatus('running');
        setAgents([]);
        setReportData(null);
        setLogs([{ time: formatTime(), msg: 'Submitting job allocation request...', level: 'info' }]);

        try {
            const token = localStorage.getItem('autoops_token');
            let uploadedFileId = null;

            if (file) {
                addLog(`Uploading block attachment: ${file.name}...`, 'info');
                const fd = new FormData();
                fd.append('file', file);
                const fileRes = await fetch(`${API_BASE}/files/upload`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                    body: fd
                });
                const fileData = await fileRes.json();
                if (!fileRes.ok) throw new Error('File upload failed');
                uploadedFileId = fileData.id;
                addLog('File synchronized to vector space successfully', 'success');
            }

            const res = await fetch(`${API_BASE}/workflow/run`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ input_text: prompt, file_id: uploadedFileId })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Workflow dispatch failed');

            setWorkflowId(data.workflow_id); // triggers SSE hook
        } catch (err) {
            setStatus('error');
            addLog(`Submission rejected: ${err.message}`, 'error');
        }
    };
    
    // --- Parse Report Data gracefully ---
    let reportText = null;
    let csvAnalysis = null;
    let fallbackSummaries = [];
    
    if (reportData && reportData.results) {
        reportData.results.forEach(r => {
            if (r.tool_result?.report) reportText = r.tool_result.report;
            if (r.tool_result?.analysis) csvAnalysis = r.tool_result.analysis;
            if (r.tool_result?.summary) reportText = r.tool_result.summary; // LLM summarizer
            if (r.summary) fallbackSummaries.push({ agent: r.agent, txt: r.summary });
        });
    }

    return (
        <React.Fragment>
            <div className="page-header">
                <h1>▶️ Run Workflow</h1>
                <p>Describe your multi-agent architecture pipeline execution parameters.</p>
            </div>

            <div className="card workflow-input-area" style={{ background: 'var(--bg-card)', marginBottom: '2rem' }}>
                <textarea className="workflow-textarea form-input" style={{ width: '100%', minHeight: '120px' }} placeholder="E.g. Analyze the uploaded dataset, schedule a sync review next Friday at 10AM, and email the report summary to our admin channel..." value={prompt} onChange={e => setPrompt(e.target.value)} disabled={status === 'running'}></textarea>

                <div className="upload-zone mt-2" onClick={() => document.getElementById('wfFileInput').click()} style={{ border: '2px dashed var(--border-color)', background: 'var(--bg-secondary)', padding: '2rem', textAlign: 'center', cursor: 'pointer', borderRadius: '8px', transition: 'border-color 0.2s' }}>
                    <div className="icon" style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📎</div>
                    <p>Drag & drop attachments or <strong>browse local disk</strong></p>
                    <input type="file" id="wfFileInput" style={{ display: 'none' }} accept=".csv,.xlsx,.pdf,.txt" onChange={(e) => setFile(e.target.files[0])} disabled={status === 'running'} />
                </div>
                
                {file && (
                    <div className="file-attached mt-2" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                        <span style={{ fontSize: '1.5rem' }}>📄</span>
                        <span style={{ flex: 1, fontWeight: '600' }}>{file.name}</span>
                        <button className="btn btn-ghost" onClick={() => setFile(null)} style={{ color: 'var(--error)' }}>✕</button>
                    </div>
                )}

                <div className="workflow-actions" style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
                    <button className="btn btn-primary btn-lg" onClick={runWorkflow} disabled={!prompt || status === 'running'}>{status === 'running' ? '🚀 Allocating Agents...' : 'Run Pipeline'}</button>
                </div>
            </div>

            {(workflowId || status === 'running') && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    
                    {/* Execution Engine UI Section */}
                    {agents.length > 0 && (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', alignItems: 'stretch' }}>
                            <div className="card" style={{ background: 'var(--bg-card)', flex: 1 }}>
                                <div className="card-header">
                                    <h3 className="card-title">🤖 Active Agents ({agents.length})</h3>
                                    <span className="badge badge-running">Orchestrator Online</span>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '520px', overflowY: 'auto' }}>
                                    {agents.map(a => (
                                        <div key={a.name} style={{ background: 'var(--bg-secondary)', padding: '1rem 1.25rem', borderRadius: '10px', border: `1px solid ${a.status === 'running' ? 'rgba(66,139,255,0.5)' : 'var(--border-color)'}`, display: 'flex', flexDirection: 'column', gap: '6px', boxShadow: a.status === 'running' ? '0 0 16px rgba(66,139,255,0.15)' : 'none', transition: 'all 0.3s ease' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                    <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: a.status === 'completed' ? 'var(--success)' : a.status === 'running' ? 'var(--info)' : a.status === 'failed' ? 'var(--error)' : 'var(--text-muted)', boxShadow: a.status === 'running' ? '0 0 10px rgba(66, 139, 255, 0.7)' : 'none', animation: a.status === 'running' ? 'pulse 1.5s infinite' : 'none' }}></span>
                                                    <span style={{ fontWeight: '700', fontSize: '0.95rem' }}>{a.name}</span>
                                                </div>
                                                <span style={{ fontSize: '0.72rem', padding: '2px 10px', borderRadius: '12px', background: a.status === 'completed' ? 'rgba(16,185,129,0.15)' : a.status === 'running' ? 'rgba(66,139,255,0.15)' : 'var(--bg-card)', color: a.status === 'completed' ? 'var(--success)' : a.status === 'running' ? 'var(--info)' : 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600', letterSpacing: '0.05em' }}>{a.status}</span>
                                            </div>
                                            {a.tool && <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', paddingLeft: '1.5rem' }}>🔧 Tool binding: <code style={{ background: 'var(--bg-card)', padding: '1px 6px', borderRadius: '4px', color: '#fbbf24' }}>{a.tool}</code></div>}
                                            {a.description && <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', paddingLeft: '1.5rem', fontStyle: 'italic' }}>{a.description}</div>}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="card" style={{ background: 'var(--bg-card)', flex: 1 }}>
                                <div className="card-header">
                                    <h3 className="card-title">🔀 Execution Graph (DAG)</h3>
                                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Directed Acyclic Graph</span>
                                </div>
                                <div style={{ minHeight: '480px' }}>
                                    <DAGGraph agentsConfig={agents} />
                                </div>
                            </div>
                        </div>
                    )}

                    <div className="card" style={{ background: 'var(--bg-card)' }}>
                        <div className="card-header">
                            <h3 className="card-title" style={{ fontSize: '1.4rem' }}>📡 Interactive Command Logs</h3>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{logs.length} entries</span>
                                <span className={`badge badge-${status === 'running' ? 'running' : status === 'done' ? 'success' : 'error'}`}>{status.toUpperCase()}</span>
                            </div>
                        </div>
                        <div className="logs-terminal" style={{ background: '#0d1117', color: '#c9d1d9', padding: '1.75rem 2rem', borderRadius: '8px', height: '600px', overflowY: 'auto', fontFamily: '"Fira Code", "Cascadia Code", monospace', fontSize: '13.5px', lineHeight: '2', border: '1px solid var(--glass-border)', boxShadow: 'inset 0 4px 20px rgba(0,0,0,0.5)' }}>
                            {logs.map((log, i) => {
                                const levelColor = {
                                    info: '#79c0ff',
                                    success: '#56d364',
                                    warning: '#e3b341',
                                    error: '#f85149'
                                };
                                return (
                                    <div key={i} style={{ marginBottom: '2px', color: levelColor[log.level] || levelColor.info, display: 'flex', gap: '12px' }}>
                                        <span style={{ color: '#484f58', flexShrink: 0, userSelect: 'none' }}>[{log.time}]</span>
                                        <span style={{ flex: 1 }}>{log.msg}</span>
                                    </div>
                                )
                            })}
                            <div ref={logsEndRef} />
                        </div>
                    </div>

                    {reportData && (
                        <div>
                            {/* Analysis Metrics */}
                            {csvAnalysis && (
                                <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
                                    <div className="stat-card" style={{ background: 'var(--bg-card)' }}><div className="stat-label">Total Rows</div><div className="stat-value">{csvAnalysis.total_rows?.toLocaleString() || 0}</div></div>
                                    <div className="stat-card" style={{ background: 'var(--bg-card)' }}><div className="stat-label">Columns</div><div className="stat-value">{csvAnalysis.total_columns || 0}</div></div>
                                    <div className="stat-card" style={{ background: 'var(--bg-card)' }}><div className="stat-label">Missing Values</div><div className="stat-value">{csvAnalysis.missing_values || 0}</div></div>
                                    <div className="stat-card" style={{ background: 'var(--bg-card)' }}><div className="stat-label">Numeric Columns</div><div className="stat-value">{(csvAnalysis.numeric_columns || []).length}</div></div>
                                </div>
                            )}

                            {/* Final Output Card */}
                            {reportText ? (
                                <div className="card" style={{ background: 'var(--bg-card)', marginBottom: '1.5rem' }}>
                                    <div className="card-header"><h3 className="card-title">📊 Final Compilation Report</h3></div>
                                    <div className="report-body" style={{ padding: '1.5rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '8px', lineHeight: '1.7' }}>
                                        <div dangerouslySetInnerHTML={{ __html: renderMarkdown(reportText) }}></div>
                                    </div>
                                </div>
                            ) : fallbackSummaries.length > 0 && (
                                <div className="card" style={{ background: 'var(--bg-card)', marginBottom: '1.5rem' }}>
                                    <div className="card-header"><h3 className="card-title">📊 Individual Agent Artifacts</h3></div>
                                    <div className="report-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                        {fallbackSummaries.map((s, i) => (
                                            <div key={i} style={{ background: 'var(--bg-secondary)', padding: '1.5rem', borderRadius: '8px', borderLeft: '4px solid var(--accent-primary)' }}>
                                                <h4 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>🤖 {s.agent}</h4>
                                                <div dangerouslySetInnerHTML={{ __html: renderMarkdown(s.txt) }} style={{ color: 'var(--text-secondary)' }}></div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Raw JSON Inspect */}
                            <details className="card" style={{ background: 'var(--bg-card)' }}>
                                <summary className="card-header" style={{ cursor: 'pointer', outline: 'none' }}><h3 className="card-title">🔧 Core Debug Output</h3></summary>
                                <div style={{ padding: '1.5rem' }}>
                                    <pre style={{ whiteSpace: 'pre-wrap', background: 'var(--bg-secondary)', padding: '1.5rem', borderRadius: '8px', border: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                                        {JSON.stringify(reportData, null, 2)}
                                    </pre>
                                </div>
                            </details>
                        </div>
                    )}
                </div>
            )}
        </React.Fragment>
    );
}
