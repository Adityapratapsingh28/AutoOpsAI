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

const inputStyle = {
    width: '100%',
    padding: '12px 16px',
    border: '1px solid #c1c1c1',
    borderRadius: '8px',
    fontSize: '14px',
    fontFamily: 'inherit',
    color: '#222222',
    boxSizing: 'border-box'
};

export default function ManagerTeams() {
    const [teams, setTeams] = useState([]);
    const [members, setMembers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [newTeamName, setNewTeamName] = useState('');
    const [newTeamDesc, setNewTeamDesc] = useState('');
    const [users, setUsers] = useState([]);
    const [assignUserId, setAssignUserId] = useState('');
    const [assignTeamId, setAssignTeamId] = useState('');
    const [assignRole, setAssignRole] = useState('Member');
    const navigate = useNavigate();

    const fetchTeamsAndMembers = async () => {
        try {
            const token = localStorage.getItem('autoops_token');
            if (!token) return navigate('/');

            const [teamsRes, membersRes, usersRes] = await Promise.all([
                fetch(`${API_BASE}/manager/teams`, { headers: { 'Authorization': `Bearer ${token}` } }),
                fetch(`${API_BASE}/manager/members`, { headers: { 'Authorization': `Bearer ${token}` } }),
                fetch(`${API_BASE}/manager/users_list`, { headers: { 'Authorization': `Bearer ${token}` } })
            ]);

            if (teamsRes.ok) setTeams(await teamsRes.json());
            if (membersRes.ok) setMembers(await membersRes.json());
            if (usersRes.ok) setUsers(await usersRes.json());
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTeamsAndMembers();
    }, []);

    const handleCreateTeam = async (e) => {
        e.preventDefault();
        if (!newTeamName) return;
        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch(`${API_BASE}/manager/teams`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: newTeamName, description: newTeamDesc })
            });
            if (res.ok) {
                setNewTeamName('');
                setNewTeamDesc('');
                fetchTeamsAndMembers();
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleAssignMember = async (e) => {
        e.preventDefault();
        if (!assignUserId || !assignTeamId) return;
        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch(`${API_BASE}/manager/members`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_id: parseInt(assignUserId), team_id: parseInt(assignTeamId), designation: assignRole })
            });
            if (res.ok) {
                setAssignUserId('');
                setAssignTeamId('');
                setAssignRole('Member');
                fetchTeamsAndMembers();
            } else {
                const data = await res.json();
                alert(data.detail || "Failed to assign member");
            }
        } catch (err) {
            console.error(err);
        }
    };

    if (loading) return <div style={{ padding: '2rem', color: '#222222' }}>Loading teams...</div>;

    return (
        <div style={{ padding: '24px', fontFamily: '"Airbnb Cereal VF", Circular, -apple-system, sans-serif' }}>
            <div style={{ marginBottom: '32px' }}>
                <h1 style={{ fontSize: '28px', fontWeight: '700', color: '#222222', letterSpacing: '-0.44px', marginBottom: '8px' }}>
                    Teams & Members
                </h1>
                <p style={{ fontSize: '16px', color: '#6a6a6a', margin: 0 }}>
                    Manage organizational structure and AI provisioning
                </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 2fr', gap: '24px' }}>
                {/* Create Team Form */}
                <div style={cardStyle}>
                    <h2 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '16px' }}>Create New Team</h2>
                    <form onSubmit={handleCreateTeam} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div>
                            <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#3f3f3f' }}>Team Name</label>
                            <input 
                                style={inputStyle}
                                value={newTeamName} 
                                onChange={e => setNewTeamName(e.target.value)} 
                                placeholder="e.g. Engineering" 
                            />
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#3f3f3f' }}>Description</label>
                            <input 
                                style={inputStyle}
                                value={newTeamDesc} 
                                onChange={e => setNewTeamDesc(e.target.value)} 
                                placeholder="What does this team do?" 
                            />
                        </div>
                        <button type="submit" style={{ 
                            background: '#222222', color: '#ffffff', padding: '12px', 
                            borderRadius: '8px', fontSize: '16px', fontWeight: '500', 
                            border: 'none', cursor: 'pointer', marginTop: '8px' 
                        }}>
                            Add Team
                        </button>
                    </form>
                </div>

                {/* Assign Member Form */}
                <div style={cardStyle}>
                    <h2 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '16px' }}>Assign Member</h2>
                    <form onSubmit={handleAssignMember} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div>
                            <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#3f3f3f' }}>Select User</label>
                            <select 
                                style={inputStyle}
                                value={assignUserId} 
                                onChange={e => setAssignUserId(e.target.value)} 
                                required
                            >
                                <option value="" disabled>-- Select a User --</option>
                                {users.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>)}
                            </select>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#3f3f3f' }}>Select Team</label>
                            <select 
                                style={inputStyle}
                                value={assignTeamId} 
                                onChange={e => setAssignTeamId(e.target.value)} 
                                required
                            >
                                <option value="" disabled>-- Select a Team --</option>
                                {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                            </select>
                        </div>
                        <div>
                            <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#3f3f3f' }}>Designation</label>
                            <input 
                                style={inputStyle}
                                value={assignRole} 
                                onChange={e => setAssignRole(e.target.value)} 
                                placeholder="e.g. Engineer, Manager" 
                            />
                        </div>
                        <button type="submit" style={{ 
                            background: '#ff385c', color: '#ffffff', padding: '12px', 
                            borderRadius: '8px', fontSize: '16px', fontWeight: '500', 
                            border: 'none', cursor: 'pointer', marginTop: '8px' 
                        }}>
                            Assign Member
                        </button>
                    </form>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr)', gap: '24px', marginTop: '24px' }}>
                {/* Team List */}
                <div style={{ ...cardStyle }}>
                    <h2 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '16px' }}>Active Teams</h2>
                    {teams.length === 0 ? <p style={{color: '#6a6a6a'}}>No teams created yet.</p> : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {teams.map(t => (
                                <div key={t.id} style={{ padding: '16px', border: '1px solid #e8e8e8', borderRadius: '12px', background: '#fafafa' }}>
                                    <div style={{ fontWeight: '600', fontSize: '16px', color: '#222222' }}>{t.name}</div>
                                    <div style={{ fontSize: '13px', color: '#6a6a6a', marginTop: '4px' }}>{t.description || "No description"}</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Members List */}
            <div style={{ ...cardStyle, marginTop: '32px', padding: 0 }}>
                 <div style={{ padding: '24px', borderBottom: '1px solid #c1c1c1' }}>
                    <h2 style={{ fontSize: '22px', fontWeight: '600', margin: 0 }}>Org Members</h2>
                </div>
                <div style={{ padding: '0 24px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                        <thead>
                            <tr>
                                <th style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontSize: '13px', fontWeight: '600' }}>Name</th>
                                <th style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontSize: '13px', fontWeight: '600' }}>Team</th>
                                <th style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontSize: '13px', fontWeight: '600' }}>Role</th>
                                <th style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', color: '#6a6a6a', fontSize: '13px', fontWeight: '600' }}>Email</th>
                            </tr>
                        </thead>
                        <tbody>
                            {members.length === 0 ? (
                                <tr>
                                    <td colSpan="4" style={{ padding: '24px 0', textAlign: 'center', color: '#6a6a6a' }}>No members provisioned yet.</td>
                                </tr>
                            ) : members.map(m => (
                                <tr key={m.id}>
                                    <td style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', fontSize: '14px', fontWeight: '500', color: '#222222' }}>{m.full_name}</td>
                                    <td style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', fontSize: '14px', color: '#6a6a6a' }}>{m.team_name}</td>
                                    <td style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', fontSize: '14px', color: '#6a6a6a', textTransform: 'capitalize' }}>{m.role}</td>
                                    <td style={{ padding: '16px 0', borderBottom: '1px solid #e8e8e8', fontSize: '14px', color: '#428bff' }}>{m.work_email}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
