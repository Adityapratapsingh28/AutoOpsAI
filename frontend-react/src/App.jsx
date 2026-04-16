import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import SignIn from './pages/SignIn';
import OTPVerification from './pages/OTPVerification';
import Dashboard from './pages/Dashboard';
import Workflow from './pages/Workflow';
import History from './pages/History';
import Files from './pages/Files';
import Schedule from './pages/Schedule';
import Settings from './pages/Settings';
import ManagerDashboard from './pages/ManagerDashboard';
import ManagerTeams from './pages/ManagerTeams';
import ManagerReports from './pages/ManagerReports';
import ManagerLogs from './pages/ManagerLogs';
import Governance from './pages/Governance';
import './css/styles.css';

function Sidebar() {
    const location = useLocation();
    const navigate = useNavigate();
    const isActive = (path) => location.pathname === path ? "nav-link active" : "nav-link";

    // Load user safely
    let user = { full_name: "User", role: "employee" };
    try {
        const stored = localStorage.getItem('autoops_user');
        if (stored) user = JSON.parse(stored);
    } catch (e) {}

    const handleLogout = (e) => {
        e.preventDefault();
        localStorage.removeItem('autoops_token');
        localStorage.removeItem('autoops_user');
        navigate('/');
    };

    return (
        <aside className="sidebar" id="sidebar">
            <div className="sidebar-logo">
                <h2>AUTOPS AI</h2>
                <span>AI Workflow Engine</span>
            </div>
            <nav className="sidebar-nav">
                {user.role === 'manager' || user.role === 'admin' ? (
                    <>
                        <div className="nav-section">
                            <div className="nav-section-title">Manager Portal</div>
                            <Link to="/manager/dashboard" className={isActive("/manager/dashboard")}>
                                <span className="icon">📈</span> Overview
                            </Link>
                            <Link to="/manager/teams" className={isActive("/manager/teams")}>
                                <span className="icon">👥</span> Teams & Members
                            </Link>
                            <Link to="/manager/reports" className={isActive("/manager/reports")}>
                                <span className="icon">📑</span> Report Hub
                            </Link>
                            <Link to="/manager/logs" className={isActive("/manager/logs")}>
                                <span className="icon">🛡️</span> Audit Logs
                            </Link>
                            <Link to="/manager/governance" className={isActive("/manager/governance")}>
                                <span className="icon">⚖️</span> Governance
                            </Link>
                        </div>
                        <div className="nav-section">
                            <div className="nav-section-title">Personal Execution</div>
                            <Link to="/workflow" className={isActive("/workflow")}>
                                <span className="icon">▶️</span> Run Workflow
                            </Link>
                        </div>
                    </>
                ) : (
                    <>
                        <div className="nav-section">
                            <div className="nav-section-title">Main</div>
                            <Link to="/dashboard" className={isActive("/dashboard")}>
                                <span className="icon">📊</span> Dashboard
                            </Link>
                            <Link to="/workflow" className={isActive("/workflow")}>
                                <span className="icon">▶️</span> Run Workflow
                            </Link>
                            <Link to="/history" className={isActive("/history")}>
                                <span className="icon">📋</span> My Workflows
                            </Link>
                        </div>
                        <div className="nav-section">
                            <div className="nav-section-title">Resources</div>
                            <Link to="/files" className={isActive("/files")}>
                                <span className="icon">📁</span> Files
                            </Link>
                            <Link to="/schedule" className={isActive("/schedule")}>
                                <span className="icon">📅</span> Schedule
                            </Link>
                        </div>
                    </>
                )}
                <div className="nav-section">
                    <Link to="/settings" className={isActive("/settings")}>
                        <span className="icon">⚙️</span> Settings
                    </Link>
                    <a href="/" className="nav-link" onClick={handleLogout}>
                        <span className="icon">🚪</span> Sign Out
                    </a>
                </div>
            </nav>
            <div className="sidebar-footer">
                <div className="user-widget">
                    <div className="user-avatar" id="userAvatar">{(user.full_name || 'U').charAt(0).toUpperCase()}</div>
                    <div className="user-info">
                        <div className="name" id="userName">{user.full_name || 'User'}</div>
                        <div className="role" id="userRole">{user.role || 'employee'}</div>
                    </div>
                </div>
            </div>
            <button id="themeToggleBtn" style={{background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', borderRadius: '50%', padding: '4px'}}>🌙</button>
        </aside>
    );
}

function Layout({ children }) {
    return (
        <div className="app-layout">
            <Sidebar />
            <main className="main-content">
                {children}
            </main>
        </div>
    );
}

export default function App() {
    return (
        <BrowserRouter>
            <div className="bg-mesh"></div>
            <Routes>
                <Route path="/" element={<SignIn />} />
                <Route path="/verify-otp" element={<OTPVerification />} />
                <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
                <Route path="/workflow" element={<Layout><Workflow /></Layout>} />
                <Route path="/history" element={<Layout><History /></Layout>} />
                <Route path="/files" element={<Layout><Files /></Layout>} />
                <Route path="/schedule" element={<Layout><Schedule /></Layout>} />
                <Route path="/settings" element={<Layout><Settings /></Layout>} />
                
                {/* Manager Routes */}
                <Route path="/manager/dashboard" element={<Layout><ManagerDashboard /></Layout>} />
                <Route path="/manager/teams" element={<Layout><ManagerTeams /></Layout>} />
                <Route path="/manager/reports" element={<Layout><ManagerReports /></Layout>} />
                <Route path="/manager/logs" element={<Layout><ManagerLogs /></Layout>} />
                <Route path="/manager/governance" element={<Layout><Governance /></Layout>} />
            </Routes>
            <div className="toast-container" id="toastContainer"></div>
        </BrowserRouter>
    );
}
