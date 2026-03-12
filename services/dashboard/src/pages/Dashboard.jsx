import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listScans } from '../api.js'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = ['#e53e3e', '#dd6b20', '#d69e2e', '#38a169', '#718096']

function StatCard({ label, value, color }) {
  return (
    <div style={{
      background: 'white', borderRadius: 12, padding: '1.25rem 1.5rem',
      boxShadow: '0 2px 8px rgba(0,0,0,0.07)', flex: 1, minWidth: 140,
    }}>
      <div style={{ fontSize: '2rem', fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: '0.85rem', color: '#718096', marginTop: 4 }}>{label}</div>
    </div>
  )
}

const statusColor = { completed: '#38a169', running: '#2b6cb0', pending: '#d69e2e', failed: '#e53e3e' }

export default function Dashboard() {
  const [scans, setScans] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listScans(20).then(r => { setScans(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const completed = scans.filter(s => s.status === 'completed')
  const avgScore = completed.length
    ? Math.round(completed.reduce((acc, s) => acc + (s.compliance_score || 0), 0) / completed.length)
    : null

  // Build severity distribution from findings summaries
  const severityMap = {}
  completed.forEach(s => {
    const bySev = s.findings_summary?.by_severity || {}
    Object.entries(bySev).forEach(([sev, cnt]) => {
      severityMap[sev] = (severityMap[sev] || 0) + cnt
    })
  })
  const pieData = Object.entries(severityMap).map(([name, value]) => ({ name, value }))

  if (loading) return <p>Loading…</p>

  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem', color: '#1a365d' }}>Dashboard</h1>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
        <StatCard label="Total Scans" value={scans.length} color="#2b6cb0" />
        <StatCard label="Completed" value={completed.length} color="#38a169" />
        <StatCard label="Running" value={scans.filter(s => s.status === 'running').length} color="#2b6cb0" />
        <StatCard label="Failed" value={scans.filter(s => s.status === 'failed').length} color="#e53e3e" />
        {avgScore !== null && <StatCard label="Avg Compliance Score" value={`${avgScore}/100`} color={avgScore >= 80 ? '#38a169' : avgScore >= 50 ? '#d69e2e' : '#e53e3e'} />}
      </div>

      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
        {/* Findings pie */}
        {pieData.length > 0 && (
          <div style={{ background: 'white', borderRadius: 12, padding: '1.5rem', flex: 1, minWidth: 280, boxShadow: '0 2px 8px rgba(0,0,0,0.07)' }}>
            <h2 style={{ fontSize: '1rem', marginBottom: '1rem', color: '#2d3748' }}>Findings by Severity</h2>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Recent scans */}
        <div style={{ background: 'white', borderRadius: 12, padding: '1.5rem', flex: 2, minWidth: 320, boxShadow: '0 2px 8px rgba(0,0,0,0.07)' }}>
          <h2 style={{ fontSize: '1rem', marginBottom: '1rem', color: '#2d3748' }}>Recent Scans</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
            <thead>
              <tr>
                {['Project', 'Type', 'Status', 'Score', 'Actions'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '2px solid #e2e8f0', color: '#4a5568' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scans.slice(0, 8).map(s => (
                <tr key={s.id}>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #e2e8f0' }}>{s.project_name}</td>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #e2e8f0' }}>{s.scan_type.toUpperCase()}</td>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #e2e8f0' }}>
                    <span style={{
                      background: statusColor[s.status] + '20',
                      color: statusColor[s.status],
                      padding: '0.15rem 0.5rem', borderRadius: 9999, fontWeight: 600, fontSize: '0.78rem',
                    }}>{s.status}</span>
                  </td>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #e2e8f0' }}>
                    {s.compliance_score != null ? `${s.compliance_score}/100` : '—'}
                  </td>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #e2e8f0' }}>
                    {s.report_url && (
                      <Link to={`/scans/${s.id}/report`} style={{ color: '#2b6cb0', fontSize: '0.82rem' }}>View Report</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
