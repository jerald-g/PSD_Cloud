import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createScan } from '../api.js'

const EXAMPLE_TARGETS = [
  { name: 'Vulnerable API (.NET)', repo: '', url: 'http://host.docker.internal:5000' },
  { name: 'Vulnerable MVC (.NET)', repo: '', url: 'http://host.docker.internal:5001' },
  { name: 'Vulnerable Minimal API (.NET)', repo: '', url: 'http://host.docker.internal:5002' },
  { name: 'NodeGoat (OWASP, small)', repo: 'https://github.com/OWASP/NodeGoat.git', url: '' },
  { name: 'Juice Shop (OWASP, large)', repo: 'https://github.com/juice-shop/juice-shop.git', url: '' },
]

export default function NewScan() {
  const [form, setForm] = useState({
    project_name: '',
    scan_type: 'sast',
    repository_url: '',
    target_url: '',
    scan_strength: 'HIGH',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const update = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const applyExample = (ex) => {
    setForm(f => ({
      ...f,
      project_name: f.project_name || ex.name.toLowerCase().replace(/[^a-z0-9]/g, '-'),
      repository_url: ex.repo || f.repository_url,
      target_url: ex.url || f.target_url,
      scan_type: ex.repo && ex.url ? 'full' : ex.repo ? 'sast' : 'dast',
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = { ...form }
      if (form.scan_type === 'sast') { delete payload.target_url; delete payload.scan_strength }
      if (form.scan_type === 'dast') delete payload.repository_url
      await createScan(payload)
      navigate('/scans')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start scan')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '0.6rem 0.8rem', border: '1px solid #e2e8f0',
    borderRadius: 8, fontSize: '0.95rem', marginBottom: '1.25rem', boxSizing: 'border-box',
  }
  const labelStyle = { display: 'block', marginBottom: '0.3rem', fontSize: '0.85rem', fontWeight: 600, color: '#4a5568' }

  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem', color: '#1a365d' }}>New Security Scan</h1>

      <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
        {/* Scan form */}
        <div style={{ background: 'white', borderRadius: 12, padding: '2rem', flex: 2, minWidth: 360, boxShadow: '0 2px 8px rgba(0,0,0,0.07)' }}>
          {error && (
            <div style={{ background: '#fed7d7', color: '#c53030', padding: '0.75rem', borderRadius: 8, marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>
          )}
          <form onSubmit={handleSubmit}>
            <label style={labelStyle}>Project Name</label>
            <input style={inputStyle} required value={form.project_name} onChange={e => update('project_name', e.target.value)} placeholder="my-app" />

            <label style={labelStyle}>Scan Type</label>
            <select style={inputStyle} value={form.scan_type} onChange={e => update('scan_type', e.target.value)}>
              <option value="sast">SAST - Static Analysis (scans source code)</option>
              <option value="dast">DAST - Dynamic Analysis (scans running app)</option>
              <option value="full">Full - SAST + DAST combined</option>
            </select>

            {(form.scan_type === 'sast' || form.scan_type === 'full') && (
              <>
                <label style={labelStyle}>Repository URL (Git)</label>
                <input style={inputStyle} value={form.repository_url} onChange={e => update('repository_url', e.target.value)}
                  placeholder="https://github.com/org/repo.git" required={form.scan_type !== 'dast'} />
                <p style={{ fontSize: '0.8rem', color: '#718096', marginTop: '-0.75rem', marginBottom: '1.25rem' }}>
                  The SAST scanner will clone this repo and run SonarQube analysis on it.
                </p>
              </>
            )}

            {(form.scan_type === 'dast' || form.scan_type === 'full') && (
              <>
                <label style={labelStyle}>Target URL (live application)</label>
                <input style={inputStyle} value={form.target_url} onChange={e => update('target_url', e.target.value)}
                  placeholder="http://your-app:8080" required={form.scan_type !== 'sast'} />
                <p style={{ fontSize: '0.8rem', color: '#718096', marginTop: '-0.75rem', marginBottom: '1.25rem' }}>
                  The DAST scanner will spider and actively scan this URL using OWASP ZAP.
                </p>

              </>
            )}

            <button type="submit" disabled={loading} style={{
              background: '#2b6cb0', color: 'white', border: 'none',
              padding: '0.75rem 2rem', borderRadius: 8, fontSize: '1rem', fontWeight: 600,
              cursor: 'pointer', opacity: loading ? 0.7 : 1, width: '100%',
            }}>
              {loading ? 'Starting scan...' : 'Start Scan'}
            </button>
          </form>
        </div>

        {/* Quick start panel */}
        <div style={{ flex: 1, minWidth: 260 }}>
          <div style={{ background: 'white', borderRadius: 12, padding: '1.5rem', boxShadow: '0 2px 8px rgba(0,0,0,0.07)', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '0.95rem', color: '#2d3748', marginBottom: '1rem' }}>Quick Start Examples</h3>
            <p style={{ fontSize: '0.8rem', color: '#718096', marginBottom: '1rem' }}>
              Click to auto-fill the form with a sample target:
            </p>
            {EXAMPLE_TARGETS.map((ex, i) => (
              <button key={i} onClick={() => applyExample(ex)} style={{
                display: 'block', width: '100%', textAlign: 'left', background: '#f7fafc',
                border: '1px solid #e2e8f0', borderRadius: 8, padding: '0.75rem',
                marginBottom: '0.5rem', cursor: 'pointer', fontSize: '0.85rem',
              }}>
                <strong>{ex.name}</strong>
                <div style={{ fontSize: '0.75rem', color: '#718096', marginTop: 2 }}>
                  {ex.repo ? 'SAST' : ''}{ex.repo && ex.url ? ' + ' : ''}{ex.url ? 'DAST' : ''}
                </div>
              </button>
            ))}
          </div>

          <div style={{ background: '#ebf8ff', borderRadius: 12, padding: '1.5rem', border: '1px solid #bee3f8' }}>
            <h3 style={{ fontSize: '0.95rem', color: '#2b6cb0', marginBottom: '0.5rem' }}>How it works</h3>
            <ol style={{ fontSize: '0.8rem', color: '#4a5568', paddingLeft: '1.2rem', lineHeight: 1.8 }}>
              <li>Submit a scan with a repo URL or live app URL</li>
              <li>The orchestrator queues the job via NATS</li>
              <li>SAST scanner runs SonarQube analysis on the code</li>
              <li>DAST scanner runs OWASP ZAP against the live app</li>
              <li>Compliance engine maps findings to OWASP Top 10 / CIS</li>
              <li>Report generator creates an HTML report</li>
              <li>View results on the Scan History page</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}
