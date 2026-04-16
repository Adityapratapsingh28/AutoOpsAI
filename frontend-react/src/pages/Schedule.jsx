import React, { useState, useEffect } from 'react';

const API_BASE = '/api';

export default function Schedule() {
    const [meetings, setMeetings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    
    const [title, setTitle] = useState('');
    const [timeField, setTimeField] = useState('');
    const [link, setLink] = useState('');
    
    const [currentDate, setCurrentDate] = useState(new Date());

    const loadMeetings = async () => {
        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch(`${API_BASE}/meetings`, { headers: { 'Authorization': `Bearer ${token}` } });
            const data = await res.json();
            if (res.ok) setMeetings(Array.isArray(data) ? data : []);
        } catch (err) { console.error(err); } finally { setLoading(false); }
    };

    useEffect(() => { loadMeetings(); }, []);

    const createMeeting = async (e) => {
        e.preventDefault();
        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch(`${API_BASE}/meetings`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    title: title, 
                    time: new Date(timeField).toISOString(), 
                    meeting_link: link || null
                })
            });
            if (res.ok) {
                setShowModal(false);
                setTitle(''); setTimeField(''); setLink('');
                loadMeetings();
            }
        } catch (err) {}
    }

    const deleteMeeting = async (id) => {
        if (!window.confirm('Delete this meeting?')) return;
        try {
            const token = localStorage.getItem('autoops_token');
            await fetch(`${API_BASE}/meetings/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
            loadMeetings();
        } catch (err) {}
    };

    // Calendar generation logic
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const monthName = currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    
    let daysHtml = [];
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();
    
    // Add empty slots
    for (let i = 0; i < firstDay; i++) {
        daysHtml.push(<div key={`empty-${i}`} className="calendar-cell"></div>);
    }
    
    // Day slots
    for (let d = 1; d <= daysInMonth; d++) {
        const isToday = d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
        
        let daysMeetings = meetings.filter(m => {
            if (!m.time) return false;
            let dObj = new Date(m.time);
            return dObj.getFullYear() === year && dObj.getMonth() === month && dObj.getDate() === d;
        });

        daysHtml.push(
            <div key={`day-${d}`} className={`calendar-cell ${isToday ? 'today' : ''}`}>
                <div className="day-num">{d}</div>
                <div className="calendar-events-container" style={{ marginTop: '4px', fontSize: '0.75rem', overflow: 'hidden', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    {daysMeetings.map(m => {
                        let mDate = new Date(m.time);
                        let mTimeStr = mDate.toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit', hour12: false});
                        return (
                            <div key={m.id} className="calendar-event" style={{ backgroundColor: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6', padding: '2px 6px', borderRadius: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'pointer', position: 'relative' }}>
                                {mTimeStr} {m.title}
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }

    return (
        <React.Fragment>
            <div className="page-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                    <h1>📅 Schedule</h1>
                    <p>Manage your meetings and calendar.</p>
                </div>
                <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ New Meeting</button>
            </div>
            
            <div className="card mb-2">
                <div className="card-header">
                    <button className="btn btn-ghost btn-sm" onClick={() => setCurrentDate(new Date(currentDate.setMonth(currentDate.getMonth() - 1)))}>← Prev</button>
                    <h3 className="card-title">{monthName}</h3>
                    <button className="btn btn-ghost btn-sm" onClick={() => setCurrentDate(new Date(currentDate.setMonth(currentDate.getMonth() + 1)))}>Next →</button>
                </div>
                <div className="calendar-grid">
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                        <div key={day} className="calendar-header-cell">{day}</div>
                    ))}
                    {daysHtml}
                </div>
            </div>

            <div className="card">
                <div className="card-header"><h3 className="card-title">Upcoming Meetings</h3></div>
                <div className="meeting-list">
                    {loading ? <p style={{ padding: '1rem' }}>Loading...</p> : meetings.length === 0 ? <div className="empty-state">
                        <div className="icon">📅</div>
                        <h3>No meetings</h3><p>Create a meeting or run a workflow to schedule one</p>
                    </div> : 
                        meetings.map(m => {
                            const mTime = m.time ? new Date(m.time) : null;
                            const hourStr = mTime ? mTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }).replace(' ', '') : '--:--';
                            const [h, p] = hourStr.split(/(AM|PM)/);
                            return (
                                <div key={m.id} className="meeting-card">
                                    <div className="meeting-time">
                                        <div className="hour">{h || '--'}</div>
                                        <div className="period">{p || ''}</div>
                                    </div>
                                    <div className="meeting-details">
                                        <div className="title">{m.title}</div>
                                        {m.meeting_link && <a href={m.meeting_link} className="link" target="_blank" rel="noreferrer">Join Meeting →</a>}
                                    </div>
                                    <button className="btn btn-ghost btn-sm" onClick={() => deleteMeeting(m.id)}>🗑️</button>
                                </div>
                            );
                        })
                    }
                </div>
            </div>

            {showModal && (
                <div className="modal-overlay" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal card" style={{ display: 'block', margin: '15vh auto' }}>
                        <h3 className="card-title mb-2">New Meeting</h3>
                        <form onSubmit={createMeeting}>
                            <div className="form-group">
                                <label>Title</label>
                                <input type="text" className="form-input" required value={title} onChange={e => setTitle(e.target.value)} />
                            </div>
                            <div className="form-group">
                                <label>Date & Time</label>
                                <input type="datetime-local" className="form-input" required value={timeField} onChange={e => setTimeField(e.target.value)} />
                            </div>
                            <div className="form-group">
                                <label>Meeting Link (optional)</label>
                                <input type="url" className="form-input" value={link} onChange={e => setLink(e.target.value)} />
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem' }}>
                                <button type="submit" className="btn btn-primary">Create Meeting</button>
                                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </React.Fragment>
    );
}
