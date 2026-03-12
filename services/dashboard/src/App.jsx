import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import ScanHistory from './pages/ScanHistory.jsx'
import ReportViewer from './pages/ReportViewer.jsx'
import NewScan from './pages/NewScan.jsx'
import Login from './pages/Login.jsx'
import { logout } from './api.js'

function Layout({ children }) {
  const navigate = useNavigate()
  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <nav style={{
        width: 220, background: '#1a365d', color: 'white',
        padding: '1.5rem 1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem'
      }}>
        <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.5rem', padding: '0 0.5rem' }}>
          PSD Cloud
        </div>
        {[
          { to: '/', label: 'Dashboard' },
          { to: '/scans', label: 'Scan History' },
          { to: '/scans/new', label: 'New Scan' },
        ].map(({ to, label }) => (
          <Link key={to} to={to} style={{
            color: 'rgba(255,255,255,0.85)', textDecoration: 'none',
            padding: '0.6rem 0.8rem', borderRadius: 8, fontSize: '0.9rem',
          }}
            onMouseEnter={e => e.target.style.background = 'rgba(255,255,255,0.1)'}
            onMouseLeave={e => e.target.style.background = 'transparent'}
          >{label}</Link>
        ))}
        <div style={{ marginTop: 'auto' }}>
          <button onClick={handleLogout} style={{
            width: '100%', background: 'rgba(255,255,255,0.1)', border: 'none',
            color: 'white', padding: '0.6rem', borderRadius: 8, cursor: 'pointer', fontSize: '0.9rem',
          }}>Sign out</button>
        </div>
      </nav>
      {/* Main */}
      <main style={{ flex: 1, padding: '2rem', overflowY: 'auto' }}>
        {children}
      </main>
    </div>
  )
}

function RequireAuth({ children }) {
  const token = localStorage.getItem('psd_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={
          <RequireAuth><Layout><Dashboard /></Layout></RequireAuth>
        } />
        <Route path="/scans" element={
          <RequireAuth><Layout><ScanHistory /></Layout></RequireAuth>
        } />
        <Route path="/scans/new" element={
          <RequireAuth><Layout><NewScan /></Layout></RequireAuth>
        } />
        <Route path="/scans/:id/report" element={
          <RequireAuth><Layout><ReportViewer /></Layout></RequireAuth>
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
