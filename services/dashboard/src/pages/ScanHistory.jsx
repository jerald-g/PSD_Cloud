import React, { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { listScans } from '../api.js'

const statusColor = { completed: '#38a169', running: '#2b6cb0', pending: '#d69e2e', failed: '#e53e3e' }

export default function ScanHistory() {
  const [scans, setScans] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  const fetchScans = useCallback(() => {
    listScans(20).then(r => { setScans(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchScans()
    const interval = setInterval(fetchScans, 15000)
    return () => clearInterval(interval)
  }, [fetchScans])

  const displayed = filter === 'all' ? scans : scans.filter(s => s.status === filter)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ color: '#1a365d' }}>Scan History</h1>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.75rem', color: '#a0aec0' }}>Auto-refreshes every 15s</span>
          <Link to="/scans/new" style={{
            background: '#2b6cb0', color: 'white', padding: '0.6rem 1.2rem',
            borderRadius: 8, textDecoration: 'none', fontWeight: 600, fontSize: '0.9rem',
          }}>+ New Scan</Link>
        </div>
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        {['all', 'completed', 'running', 'pending', 'failed'].map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{
            padding: '0.4rem 1rem', borderRadius: 9999, border: 'none', cursor: 'pointer',
            background: filter === f ? '#2b6cb0' : '#e2e8f0',
            color: filter === f ? 'white' : '#4a5568', fontSize: '0.85rem', fontWeight: 600,
          }}>{f.charAt(0).toUpperCase() + f.slice(1)}</button>
        ))}
      </div>

      <div style={{ background: 'white', borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.07)', overflow: 'hidden' }}>
        {loading ? (
          <p style={{ padding: '2rem', textAlign: 'center', color: '#718096' }}>Loading...</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ background: '#f7fafc' }}>
                {['Project', 'Type', 'Status', 'Score', 'Total Findings', 'Started', 'Actions'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '0.75rem 1rem', color: '#4a5568', fontWeight: 600, borderBottom: '2px solid #e2e8f0' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayed.map(s => (
                <tr key={s.id}>
                  <td style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #e2e8f0', fontWeight: 500 }}>{s.project_name}</td>
                  <td style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #e2e8f0' }}>{s.scan_type.toUpperCase()}</td>
                  <td style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #e2e8f0' }}>
                    <span style={{
                      background: (statusColor[s.status] || '#718096') + '20',
                      color: statusColor[s.status] || '#718096',
                      padding: '0.2rem 0.6rem', borderRadius: 9999, fontWeight: 600, fontSize: '0.78rem',
                    }}>
                      {s.status === 'running' ? 'Running...' : s.status}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #e2e8f0' }}>
                    {s.compliance_score != null ? (
                      <span style={{ color: s.compliance_score >= 80 ? '#38a169' : s.compliance_score >= 50 ? '#d69e2e' : '#e53e3e', fontWeight: 600 }}>
                        {s.compliance_score}/100
                      </span>
                    ) : '—'}
                  </td>
                  <td style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #e2e8f0' }}>
                    {s.findings_summary?.total ?? '—'}
                  </td>
                  <td style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #e2e8f0', fontSize: '0.8rem', color: '#718096' }}>
                    {s.started_at ? new Date(s.started_at).toLocaleString() : '—'}
                  </td>
                  <td style={{ padding: '0.75rem 1rem', borderBottom: '1px solid #e2e8f0' }}>
                    {s.status === 'completed' && (
                      <Link to={`/scans/${s.id}/report`} style={{ color: '#2b6cb0', fontSize: '0.82rem', fontWeight: 600 }}>
                        View Report
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
              {displayed.length === 0 && (
                <tr><td colSpan={7} style={{ padding: '2rem', textAlign: 'center', color: '#718096' }}>
                  No scans found. <Link to="/scans/new" style={{ color: '#2b6cb0' }}>Start your first scan</Link>
                </td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
