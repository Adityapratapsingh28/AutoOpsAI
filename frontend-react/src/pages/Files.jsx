import React, { useState, useEffect, useRef } from 'react';

const API_BASE = '/api';

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

export default function Files() {
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);

    // Insight Panel State
    const [summaryFile, setSummaryFile] = useState(null);
    const [summaryResult, setSummaryResult] = useState('');
    const [summaryLoading, setSummaryLoading] = useState(false);
    const insightRef = useRef(null);

    // Ask Panel State
    const [askFile, setAskFile] = useState(null);
    const [chatLogs, setChatLogs] = useState([]);
    const [askInput, setAskInput] = useState('');
    const [askLoading, setAskLoading] = useState(false);
    const askPanelRef = useRef(null);
    const chatEndRef = useRef(null);

    const loadFiles = async () => {
        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch(`${API_BASE}/files`, { headers: { 'Authorization': `Bearer ${token}` } });
            const data = await res.json();
            if (res.ok) setFiles(Array.isArray(data) ? data : []);
        } catch (err) { console.error(err); } finally { setLoading(false); }
    };

    useEffect(() => { loadFiles(); }, []);

    useEffect(() => {
        if (chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }, [chatLogs]);

    const uploadFile = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        setUploading(true);
        const formData = new FormData();
        formData.append('file', file);
        const token = localStorage.getItem('autoops_token');
        try {
            const res = await fetch(`${API_BASE}/files/upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });
            if (res.ok) loadFiles();
        } catch (err) { console.error('Upload failed'); } finally { setUploading(false); }
    };

    const deleteFile = async (id) => {
        if (!window.confirm('Delete this file?')) return;
        try {
            const token = localStorage.getItem('autoops_token');
            await fetch(`${API_BASE}/files/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
            loadFiles();
            if (summaryFile?.id === id) setSummaryFile(null);
            if (askFile?.id === id) setAskFile(null);
        } catch (err) {}
    };

    const triggerSummarize = async (file) => {
        setAskFile(null);
        setSummaryFile(file);
        setSummaryResult('');
        setSummaryLoading(true);
        setTimeout(() => insightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);

        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch(`${API_BASE}/files/${file.id}/summarize`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({}) // Assuming an empty body depending on your FastAPI endpoint requirements
            });
            const data = await res.json();
            setSummaryResult(data.summary || 'Summary generated but empty.');
        } catch (err) {
            setSummaryResult(`❌ Failed: ${err.message}`);
        } finally {
            setSummaryLoading(false);
        }
    };

    const openAskPanel = (file) => {
        setSummaryFile(null);
        setAskFile(file);
        setChatLogs([{ sender: 'bot', text: `Hi! I can answer questions about **${file.file_name}**. What would you like to know?` }]);
        setAskInput('');
        setTimeout(() => askPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    };

    const submitQuestion = async (e) => {
        e.preventDefault();
        if (!askInput.trim() || !askFile || askLoading) return;
        
        const question = askInput.trim();
        setAskInput('');
        setChatLogs(prev => [...prev, { sender: 'user', text: question }]);
        setAskLoading(true);

        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch(`${API_BASE}/files/${askFile.id}/ask`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });
            const data = await res.json();
            setChatLogs(prev => [...prev, { sender: 'bot', text: data.answer || 'I could not find an answer in the file.' }]);
        } catch (err) {
            setChatLogs(prev => [...prev, { sender: 'bot', text: `❌ Error: ${err.message}` }]);
        } finally {
            setAskLoading(false);
        }
    };

    return (
        <React.Fragment>
            <div className="page-header">
                <h1>📁 Files</h1>
                <p>Upload and manage your data files for workflow processing.</p>
            </div>
            
            <div className="card mb-2">
                <div className="upload-zone" onClick={() => document.getElementById('fileInput').click()} style={{ border: '2px dashed var(--border-color)', padding: '2rem', textAlign: 'center', cursor: 'pointer', borderRadius: '8px', background: 'var(--bg-secondary)' }}>
                    <div className="icon" style={{ fontSize: '2rem', marginBottom: '8px' }}>☁️</div>
                    <p>{uploading ? 'Uploading...' : 'Drag & drop files here, or click to browse'}</p>
                    <input type="file" id="fileInput" accept=".csv,.xlsx" style={{ display: 'none' }} onChange={uploadFile} />
                </div>
            </div>

            {/* AI Insight Panel */}
            {summaryFile && (
                <div ref={insightRef} className="card mb-2" style={{ background: 'var(--bg-card)', marginBottom: '1rem' }}>
                    <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 className="card-title">📊 {summaryLoading ? 'Summarizing...' : 'Summary:'} {summaryFile.file_name}</h3>
                        <button className="btn btn-ghost btn-sm" onClick={() => setSummaryFile(null)}>✕ Close</button>
                    </div>
                    <div className="report-body" style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '4px' }}>
                        {summaryLoading ? (
                            <span style={{ color: 'var(--text-muted)' }}>⏳ Generating AI summary... this may take a few seconds</span>
                        ) : (
                            <div dangerouslySetInnerHTML={{ __html: renderMarkdown(summaryResult) }}></div>
                        )}
                    </div>
                </div>
            )}

            {/* Ask Panel */}
            {askFile && (
                <div ref={askPanelRef} className="card mb-2" style={{ background: 'var(--bg-card)', marginBottom: '1rem' }}>
                    <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 className="card-title">💬 Ask about {askFile.file_name}</h3>
                        <button className="btn btn-ghost btn-sm" onClick={() => setAskFile(null)}>✕ Close</button>
                    </div>
                    
                    <div className="ask-chat" style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '4px', minHeight: '200px', maxHeight: '400px', overflowY: 'auto', marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {chatLogs.map((msg, i) => (
                            <div key={i} style={{ alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%' }}>
                                <div style={{ 
                                    background: msg.sender === 'user' ? 'var(--accent-primary)' : 'var(--bg-primary)', 
                                    color: msg.sender === 'user' ? '#fff' : 'var(--text-primary)',
                                    padding: '0.75rem 1rem', 
                                    borderRadius: '12px',
                                    border: msg.sender === 'bot' ? '1px solid var(--border-color)' : 'none',
                                    boxShadow: '0 2px 5px rgba(0,0,0,0.05)'
                                }} dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}></div>
                            </div>
                        ))}
                        {askLoading && (
                            <div style={{ alignSelf: 'flex-start', background: 'var(--bg-primary)', padding: '0.75rem 1rem', borderRadius: '12px', border: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                                ⏳ Thinking...
                            </div>
                        )}
                        <div ref={chatEndRef} />
                    </div>

                    <form onSubmit={submitQuestion} className="ask-input-area" style={{ display: 'flex', gap: '0.5rem' }}>
                        <input type="text" className="form-input" style={{ flex: 1 }} value={askInput} onChange={e => setAskInput(e.target.value)} placeholder="Ask a question about this file..." disabled={askLoading} />
                        <button type="submit" className="btn btn-primary" disabled={askLoading || !askInput.trim()}>Ask →</button>
                    </form>
                </div>
            )}

            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">Your Files</h3>
                    <span className="text-sm text-muted">{files.length} files</span>
                </div>
                <div className="file-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1rem', padding: '1rem' }}>
                    {loading ? <p>Loading...</p> : files.length === 0 ? <div className="empty-state" style={{ gridColumn: '1 / -1', textAlign: 'center' }}>No files yet</div> : 
                        files.map(f => (
                            <div key={f.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', background: 'var(--bg-secondary)', padding: '1.25rem', border: '1px solid var(--border-color)', borderRadius: '12px', transition: 'transform 0.2s' }}>
                                <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📄</div>
                                <div style={{ fontWeight: 600, wordBreak: 'break-all', fontSize: '1rem', lineHeight: '1.3' }}>{f.file_name}</div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(f.created_at).toLocaleDateString()}</div>
                                <div style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto', paddingTop: '1rem' }}>
                                    <button className="btn btn-ghost btn-sm" style={{ flex: 1, padding: '0.4rem', border: '1px solid var(--border-color)' }} onClick={() => triggerSummarize(f)} title="Summarize">📊</button>
                                    <button className="btn btn-ghost btn-sm" style={{ flex: 1, padding: '0.4rem', border: '1px solid var(--border-color)' }} onClick={() => openAskPanel(f)} title="Ask about this file">💬</button>
                                    <button className="btn btn-ghost btn-sm" style={{ flex: 1, padding: '0.4rem', border: '1px solid var(--border-color)', color: 'var(--error)' }} onClick={() => deleteFile(f.id)} title="Delete">🗑️</button>
                                </div>
                            </div>
                        ))
                    }
                </div>
            </div>
        </React.Fragment>
    );
}
