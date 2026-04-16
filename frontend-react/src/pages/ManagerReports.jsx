import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = '/api';

const cardStyle = {
    background: '#ffffff',
    borderRadius: '20px',
    padding: '24px',
    boxShadow: 'rgba(0,0,0,0.02) 0px 0px 0px 1px, rgba(0,0,0,0.04) 0px 2px 6px, rgba(0,0,0,0.1) 0px 4px 8px',
    color: '#222222'
};

function renderMarkdown(text) {
    if (!text) return '';
    let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    html = html.replace(/^#{1,4}\s+(.+)$/gm, '<strong style="display:block;margin-top:8px;font-size:1.1em">$1</strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/^[-•]\s+(.+)$/gm, '<div style="margin-left:16px">• $1</div>');
    html = html.replace(/\n/g, '<br/>');
    return html;
}

export default function ManagerReports() {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchReports = async () => {
            try {
                const token = localStorage.getItem('autoops_token');
                if (!token) return navigate('/');

                const res = await fetch(`${API_BASE}/manager/reports`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (res.ok) {
                    setReports(await res.json());
                }
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchReports();
    }, [navigate]);

    if (loading) return <div style={{ padding: '2rem', color: '#222222' }}>Loading reports...</div>;

    return (
        <div style={{ padding: '24px', fontFamily: '"Airbnb Cereal VF", Circular, -apple-system, sans-serif' }}>
            <div style={{ marginBottom: '32px' }}>
                <h1 style={{ fontSize: '28px', fontWeight: '700', color: '#222222', letterSpacing: '-0.44px', marginBottom: '8px' }}>
                    Report Hub
                </h1>
                <p style={{ fontSize: '16px', color: '#6a6a6a', margin: 0 }}>
                    Centralized directory for all AI-generated reports and intelligence
                </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px' }}>
                {reports.length === 0 ? (
                    <div style={{ ...cardStyle, gridColumn: '1 / -1', textAlign: 'center', padding: '48px', color: '#6a6a6a' }}>
                        No reports have been generated yet. When employees run 'report_tool', they will appear here.
                    </div>
                ) : reports.map(r => (
                    <div key={r.id} style={{ ...cardStyle, display: 'flex', flexDirection: 'column' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '600', color: '#222222', letterSpacing: '-0.18px' }}>
                                {r.title || "Automated Report"}
                            </h3>
                            <span style={{ fontSize: '12px', background: '#f2f2f2', padding: '4px 8px', borderRadius: '12px', color: '#6a6a6a', fontWeight: '500' }}>
                                By {r.author}
                            </span>
                        </div>
                        <div style={{ flex: 1, fontSize: '14px', color: '#3f3f3f', lineHeight: '1.6', maxHeight: '150px', overflowY: 'auto', marginBottom: '16px', background: '#fafafa', padding: '12px', borderRadius: '8px' }} dangerouslySetInnerHTML={{ __html: renderMarkdown(r.summary) }}>
                        </div>
                        <div style={{ marginTop: 'auto', fontSize: '12px', color: '#929292' }}>
                            Generated on {new Date(r.created_at).toLocaleString()}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
