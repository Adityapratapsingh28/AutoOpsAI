import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = 'http://127.0.0.1:8000/api';

const cardStyle = {
    background: '#ffffff',
    borderRadius: '20px',
    padding: '24px',
    boxShadow: 'rgba(0,0,0,0.02) 0px 0px 0px 1px, rgba(0,0,0,0.04) 0px 2px 6px, rgba(0,0,0,0.1) 0px 4px 8px',
    color: '#222222',
    height: '100%',
    display: 'flex',
    flexDirection: 'column'
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

const selectStyle = {
    ...inputStyle,
    appearance: 'none',
    backgroundImage: 'url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'currentColor\' stroke-width=\'2\' stroke-linecap=\'round\' stroke-linejoin=\'round\'%3e%3cpolyline points=\'6 9 12 15 18 9\'%3e%3c/polyline%3e%3c/svg%3e")',
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 1rem center',
    backgroundSize: '1em'
}

const ruleItemStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '12px',
    border: '1px solid #e8e8e8',
    borderRadius: '12px',
    background: '#fafafa',
    marginBottom: '8px',
    fontSize: '13px'
};

const btnIconStyle = {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '14px',
    marginLeft: '8px',
    opacity: 0.6,
    transition: 'opacity 0.2s'
};

export default function Governance() {
    const [roles, setRoles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    
    // Form state for Add Rule
    const [newAgentRole, setNewAgentRole] = useState('');
    const [newCategory, setNewCategory] = useState('best_practices');
    const [newRule, setNewRule] = useState('');

    // Form state for Edit Rule
    const [editMode, setEditMode] = useState(null); // { role, category, oldRule }
    const [editRuleText, setEditRuleText] = useState('');

    const navigate = useNavigate();

    const fetchPolicies = async () => {
        try {
            const token = localStorage.getItem('autoops_token');
            if (!token) return navigate('/');

            const res = await fetch(`${API_BASE}/governance/policies`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const data = await res.json();
                setRoles(data.policies || []);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPolicies();
    }, []);

    const handleAddRule = async (e) => {
        e.preventDefault();
        try {
            const token = localStorage.getItem('autoops_token');
            const roleToSubmit = newAgentRole.trim();
            if (!roleToSubmit || !newRule.trim()) return;

            const res = await fetch(`${API_BASE}/governance/policies`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    agent_role: roleToSubmit,
                    category: newCategory,
                    rule: newRule
                })
            });

            if (res.ok) {
                setNewRule('');
                setIsAddModalOpen(false);
                fetchPolicies();
            } else {
                const error = await res.json();
                alert(error.detail || "Failed to add rule");
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleEditStart = (role, category, rule) => {
        setEditMode({ role, category, oldRule: rule });
        setEditRuleText(rule);
    };

    const handleEditSave = async () => {
        if (!editRuleText.trim()) {
            setEditMode(null);
            return;
        }
        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch(`${API_BASE}/governance/policies`, {
                method: 'PATCH',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    agent_role: editMode.role,
                    category: editMode.category,
                    old_rule: editMode.oldRule,
                    new_rule: editRuleText
                })
            });

            if (res.ok) {
                setEditMode(null);
                fetchPolicies();
            } else {
                const error = await res.json();
                alert(error.detail || "Failed to update rule");
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleDelete = async (role, category, rule) => {
        if (!window.confirm("Are you sure you want to delete this rule?")) return;
        try {
            const token = localStorage.getItem('autoops_token');
            const res = await fetch(`${API_BASE}/governance/policies`, {
                method: 'DELETE',
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    agent_role: role,
                    category: category,
                    rule: rule
                })
            });

            if (res.ok) {
                fetchPolicies();
            } else {
                const error = await res.json();
                alert(error.detail || "Failed to delete rule");
            }
        } catch (err) {
            console.error(err);
        }
    };

    const renderRuleList = (role, category, rules, badgeColor, title) => {
        if (!rules || rules.length === 0) return null;
        return (
            <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ 
                        background: badgeColor, width: '10px', height: '10px', 
                        borderRadius: '50%', display: 'inline-block' 
                    }}></span>
                    <h3 style={{ fontSize: '14px', fontWeight: '600', margin: 0, textTransform: 'capitalize' }}>
                        {title}
                    </h3>
                </div>
                {rules.map((rule, idx) => {
                    const isEditing = editMode && editMode.role === role.agent_role && editMode.category === category && editMode.oldRule === rule;
                    return (
                        <div key={idx} style={ruleItemStyle}>
                            {isEditing ? (
                                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                    <textarea 
                                        style={{...inputStyle, minHeight: '60px', padding: '8px'}}
                                        value={editRuleText}
                                        onChange={(e) => setEditRuleText(e.target.value)}
                                        autoFocus
                                    />
                                    <div style={{ display: 'flex', gap: '8px' }}>
                                        <button onClick={handleEditSave} style={{ background: '#222', color: '#fff', padding: '4px 12px', borderRadius: '4px', border: 'none', cursor: 'pointer', fontSize: '12px' }}>Save</button>
                                        <button onClick={() => setEditMode(null)} style={{ background: '#e8e8e8', color: '#222', padding: '4px 12px', borderRadius: '4px', border: 'none', cursor: 'pointer', fontSize: '12px' }}>Cancel</button>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <span style={{ flex: 1, color: '#4a4a4a', lineHeight: '1.4' }}>{rule}</span>
                                    <div style={{ display: 'flex', flexShrink: 0, marginLeft: '12px' }}>
                                        <button 
                                            style={btnIconStyle} 
                                            onClick={() => handleEditStart(role.agent_role, category, rule)}
                                            onMouseOver={(e) => e.currentTarget.style.opacity = '1'}
                                            onMouseOut={(e) => e.currentTarget.style.opacity = '0.6'}
                                            title="Edit Rule"
                                        >✏️</button>
                                        <button 
                                            style={btnIconStyle} 
                                            onClick={() => handleDelete(role.agent_role, category, rule)}
                                            onMouseOver={(e) => e.currentTarget.style.opacity = '1'}
                                            onMouseOut={(e) => e.currentTarget.style.opacity = '0.6'}
                                            title="Delete Rule"
                                        >🗑️</button>
                                    </div>
                                </>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    if (loading) return <div style={{ padding: '2rem', color: '#222222' }}>Loading policies...</div>;

    return (
        <div style={{ padding: '24px', fontFamily: '"Airbnb Cereal VF", Circular, -apple-system, sans-serif' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
                <div>
                    <h1 style={{ fontSize: '28px', fontWeight: '700', color: '#222222', letterSpacing: '-0.44px', marginBottom: '8px' }}>
                        CTDE Governance
                    </h1>
                    <p style={{ fontSize: '16px', color: '#6a6a6a', margin: 0 }}>
                        Review, edit, and enforce AI agent policies and behaviors
                    </p>
                </div>
                <button 
                    onClick={() => setIsAddModalOpen(true)}
                    style={{ 
                        background: '#ff385c', color: '#ffffff', padding: '12px 20px', 
                        borderRadius: '8px', fontSize: '14px', fontWeight: '600', 
                        border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                        boxShadow: '0 2px 4px rgba(255,56,92,0.2)'
                    }}
                >
                    <span style={{ fontSize: '16px' }}>➕</span> Add Master Rule
                </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '24px' }}>
                {roles.length === 0 ? (
                    <div style={{ ...cardStyle, gridColumn: '1 / -1', textAlign: 'center', padding: '48px' }}>
                        <p style={{ color: '#6a6a6a' }}>No agent policies have been learned or created yet.</p>
                    </div>
                ) : roles.map((role, rIdx) => (
                    <div key={rIdx} style={cardStyle}>
                        <div style={{ paddingBottom: '16px', borderBottom: '1px solid #e8e8e8', marginBottom: '20px' }}>
                            <h2 style={{ fontSize: '20px', fontWeight: '600', margin: 0 }}>{role.agent_role}</h2>
                            <p style={{ fontSize: '13px', color: '#6a6a6a', margin: '4px 0 0 0' }}>Agent Persona</p>
                        </div>
                        
                        <div style={{ flex: 1, overflowY: 'auto' }}>
                            {renderRuleList(role, 'best_practices', role.best_practices, '#10b981', 'Best Practices')}
                            {renderRuleList(role, 'optimal_patterns', role.optimal_patterns, '#3b82f6', 'Optimal Patterns')}
                            {renderRuleList(role, 'common_failures', role.common_failures, '#ef4444', 'Common Failures')}
                            
                            {(!role.best_practices?.length && !role.optimal_patterns?.length && !role.common_failures?.length) && (
                                <p style={{ color: '#6a6a6a', fontSize: '13px', fontStyle: 'italic' }}>No rules established for this role.</p>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Add Rule Modal Overlay */}
            {isAddModalOpen && (
                <div style={{ 
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
                    backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
                    display: 'flex', justifyContent: 'center', alignItems: 'center',
                    backdropFilter: 'blur(4px)'
                }}>
                    <div style={{ 
                        background: '#fff', borderRadius: '16px', padding: '32px', 
                        width: '100%', maxWidth: '500px',
                        boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                            <h2 style={{ fontSize: '22px', fontWeight: '600', margin: 0 }}>Add Master Rule</h2>
                            <button 
                                onClick={() => setIsAddModalOpen(false)}
                                style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#6a6a6a' }}
                            >✕</button>
                        </div>
                        <form onSubmit={handleAddRule} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div>
                                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#3f3f3f' }}>Agent Role / Persona</label>
                                <input 
                                    style={inputStyle}
                                    list="agent-roles-list"
                                    value={newAgentRole}
                                    onChange={(e) => setNewAgentRole(e.target.value)}
                                    placeholder="e.g. Schedule Zoom Meeting"
                                    required
                                />
                                <datalist id="agent-roles-list">
                                    {roles.map(r => <option key={r.agent_role} value={r.agent_role} />)}
                                </datalist>
                                <div style={{ fontSize: '12px', color: '#6a6a6a', marginTop: '4px' }}>Type carefully; an exact match adds to an existing role.</div>
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#3f3f3f' }}>Category</label>
                                <select 
                                    style={selectStyle}
                                    value={newCategory}
                                    onChange={(e) => setNewCategory(e.target.value)}
                                >
                                    <option value="best_practices">Best Practices (Green, 🟢)</option>
                                    <option value="optimal_patterns">Optimal Patterns (Blue, 🔵)</option>
                                    <option value="common_failures">Common Failures (Red, 🔴)</option>
                                </select>
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#3f3f3f' }}>Rule Description</label>
                                <textarea 
                                    style={{...inputStyle, minHeight: '100px', resize: 'vertical'}}
                                    value={newRule}
                                    onChange={(e) => setNewRule(e.target.value)}
                                    placeholder="Describe the mandatory behavior or rule for this agent..."
                                    required
                                />
                            </div>
                            <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                                <button type="button" onClick={() => setIsAddModalOpen(false)} style={{ flex: 1, padding: '12px', background: '#f5f5f5', border: '1px solid #e8e8e8', borderRadius: '8px', color: '#222', fontWeight: '500', cursor: 'pointer' }}>Cancel</button>
                                <button type="submit" style={{ flex: 1, padding: '12px', background: '#222', border: 'none', borderRadius: '8px', color: '#fff', fontWeight: '500', cursor: 'pointer' }}>Save Rule</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
