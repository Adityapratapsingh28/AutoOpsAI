/**
 * AutoOps AI — Schedule / Calendar Page Logic
 */

if (!requireAuth()) throw new Error('Not authenticated');

let currentDate = new Date();

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
        html += `
            <div class="calendar-cell ${isToday ? 'today' : ''}">
                <div class="day-num ${isToday ? '' : ''}">${d}</div>
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
        const meetings = await apiGet('/meetings');
        const list = document.getElementById('meetingList');

        if (meetings.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="icon">📅</div>
                    <h3>No meetings</h3>
                    <p>Create a meeting or use an AI workflow to schedule one</p>
                </div>`;
            return;
        }

        list.innerHTML = meetings.map(m => {
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

renderCalendar();
loadMeetings();
