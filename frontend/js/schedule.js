/**
 * AutoOps AI — Schedule / Calendar Page Logic
 */

if (!requireAuth()) throw new Error('Not authenticated');

let currentDate = new Date();
let currentMeetings = [];

// ── Inject Tooltip Styles ──
let tooltipsStyle = document.createElement('style');
tooltipsStyle.innerHTML = `
.calendar-event {
    position: relative;
    overflow: visible !important;
}
.calendar-event .event-tooltip {
    display: none;
    position: absolute;
    bottom: 120%;
    left: 50%;
    transform: translateX(-50%);
    background: #1e293b;
    border: 1px solid #334155;
    padding: 12px;
    border-radius: 8px;
    width: 240px;
    z-index: 9999;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    white-space: normal;
    text-align: left;
    cursor: default;
}
.calendar-event:hover .event-tooltip {
    display: block;
}
.event-tooltip h4 { margin: 0 0 6px 0; color: #fff; font-size: 14px; font-weight: 600; line-height: 1.3; }
.event-tooltip p { margin: 0 0 10px 0; color: #94a3b8; font-size: 12px; display: flex; align-items: center; gap: 4px; }
.event-tooltip a { display: inline-block; background: #3b82f6; color: #fff; text-decoration: none; font-size: 12px; padding: 6px 12px; border-radius: 4px; font-weight: 500; transition: background 0.2s; }
.event-tooltip a:hover { background: #2563eb; }
.event-tooltip::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -6px;
    border-width: 6px;
    border-style: solid;
    border-color: #334155 transparent transparent transparent;
}
`;
document.head.appendChild(tooltipsStyle);

// ── Calendar Rendering ──

function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    document.getElementById('calendarTitle').textContent =
        currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const grid = document.getElementById('calendarGrid');
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();

    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    let html = days.map(d => `<div class="calendar-header-cell">${d}</div>`).join('');

    // Empty cells before first day
    for (let i = 0; i < firstDay; i++) {
        html += `<div class="calendar-cell"></div>`;
    }

    // Day cells
    for (let d = 1; d <= daysInMonth; d++) {
        const isToday = d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
        
        // Find meetings for this day
        let daysMeetings = currentMeetings.filter(m => {
            if (!m.time) return false;
            let dObj = new Date(m.time);
            return dObj.getFullYear() === year && dObj.getMonth() === month && dObj.getDate() === d;
        });

        let meetingsHtml = daysMeetings.map(m => {
            let mDate = new Date(m.time);
            let mTimeStr = mDate.toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit', hour12: false});
            let joinLinkHtml = m.meeting_link ? `<a href="${m.meeting_link}" target="_blank">Join Zoom Meeting →</a>` : '';
            return `
            <div class="calendar-event" style="background-color: rgba(59, 130, 246, 0.2); color: #3b82f6; padding: 2px 6px; border-radius: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer;">
                ${mTimeStr} ${m.title}
                <div class="event-tooltip">
                    <h4>${m.title}</h4>
                    <p>🕒 ${mTimeStr}</p>
                    ${joinLinkHtml}
                </div>
            </div>`;
        }).join('');

        html += `
            <div class="calendar-cell ${isToday ? 'today' : ''}">
                <div class="day-num">${d}</div>
                <div class="calendar-events-container" style="margin-top: 4px; font-size: 0.75rem; overflow: hidden; display: flex; flex-direction: column; gap: 2px;">
                    ${meetingsHtml}
                </div>
            </div>
        `;
    }

    grid.innerHTML = html;
}

function changeMonth(delta) {
    currentDate.setMonth(currentDate.getMonth() + delta);
    renderCalendar();
}

// ── Meetings ──

async function loadMeetings() {
    try {
        currentMeetings = await apiGet('/meetings');
        renderCalendar(); // Re-render to show meetings in the calendar grid
        const list = document.getElementById('meetingList');

        if (currentMeetings.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="icon">📅</div>
                    <h3>No meetings</h3>
                    <p>Create a meeting or use an AI workflow to schedule one</p>
                </div>`;
            return;
        }

        list.innerHTML = currentMeetings.map(m => {
            const time = m.time ? new Date(m.time) : null;
            const hour = time ? time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }).replace(' ', '') : '--:--';
            const [h, p] = hour.split(/(AM|PM)/);

            return `
                <div class="meeting-card">
                    <div class="meeting-time">
                        <div class="hour">${h || '--'}</div>
                        <div class="period">${p || ''}</div>
                    </div>
                    <div class="meeting-details">
                        <div class="title">${m.title}</div>
                        ${m.meeting_link ? `<a href="${m.meeting_link}" class="link" target="_blank">Join Meeting →</a>` : ''}
                    </div>
                    <button class="btn btn-ghost btn-sm" onclick="deleteMeeting(${m.id})">🗑️</button>
                </div>
            `;
        }).join('');
    } catch (err) {
        showToast('Failed to load meetings: ' + err.message, 'error');
    }
}

function showAddMeeting() {
    document.getElementById('meetingModal').classList.remove('hidden');
}

function closeMeetingModal(e) {
    if (e.target.id === 'meetingModal') {
        e.target.classList.add('hidden');
    }
}

async function createMeeting(e) {
    e.preventDefault();
    try {
        await apiPost('/meetings', {
            title: document.getElementById('meetingTitle').value,
            time: document.getElementById('meetingTime').value,
            meeting_link: document.getElementById('meetingLink').value || null,
        });
        document.getElementById('meetingModal').classList.add('hidden');
        showToast('Meeting created', 'success');
        loadMeetings();
    } catch (err) {
        showToast('Failed to create meeting: ' + err.message, 'error');
    }
}

async function deleteMeeting(id) {
    if (!confirm('Delete this meeting?')) return;
    try {
        await apiDelete(`/meetings/${id}`);
        showToast('Meeting deleted', 'success');
        loadMeetings();
    } catch (err) {
        showToast('Delete failed: ' + err.message, 'error');
    }
}

loadMeetings();
