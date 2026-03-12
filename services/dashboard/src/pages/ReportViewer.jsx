import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getScan, getReportHtmlUrl, getReportJsonUrl, getReportPdfUrl } from '../api.js'

export default function ReportViewer() {
  const { id } = useParams()
  const [scan, setScan] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getScan(id).then(r => { setScan(r.data); setLoading(false) }).catch(() => setLoading(false))
  }, [id])

  if (loading) return <p>Loading scan…</p>
  if (!scan) return <p>Scan not found.</p>

  const htmlUrl = getReportHtmlUrl(id)
  const jsonUrl = getReportJsonUrl(id)
  const pdfUrl = getReportPdfUrl(id)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ color: '#1a365d', marginBottom: '0.25rem' }}>{scan.project_name}</h1>
          <p style={{ color: '#718096', fontSize: '0.9rem' }}>Scan ID: {id} &nbsp;|&nbsp; Type: {scan.scan_type.toUpperCase()}</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <a href={htmlUrl} target="_blank" rel="noreferrer" style={{
            background: '#2b6cb0', color: 'white', padding: '0.6rem 1.2rem',
            borderRadius: 8, textDecoration: 'none', fontWeight: 600, fontSize: '0.9rem',
          }}>Download HTML</a>
          <a href={pdfUrl} target="_blank" rel="noreferrer" style={{
            background: '#e53e3e', color: 'white', padding: '0.6rem 1.2rem',
            borderRadius: 8, textDecoration: 'none', fontWeight: 600, fontSize: '0.9rem',
          }}>Download PDF</a>
          <a href={jsonUrl} target="_blank" rel="noreferrer" style={{
            background: '#e2e8f0', color: '#2d3748', padding: '0.6rem 1.2rem',
            borderRadius: 8, textDecoration: 'none', fontWeight: 600, fontSize: '0.9rem',
          }}>Download JSON</a>
        </div>
      </div>

      {/* Score summary */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Compliance Score', value: scan.compliance_score != null ? `${scan.compliance_score}/100` : '—', color: scan.compliance_score >= 80 ? '#38a169' : scan.compliance_score >= 50 ? '#d69e2e' : '#e53e3e' },
          { label: 'Total Findings', value: scan.findings_summary?.total ?? '—', color: '#2b6cb0' },
          { label: 'Critical', value: scan.findings_summary?.by_severity?.CRITICAL ?? 0, color: '#e53e3e' },
          { label: 'High', value: scan.findings_summary?.by_severity?.HIGH ?? 0, color: '#dd6b20' },
          { label: 'Medium', value: scan.findings_summary?.by_severity?.MEDIUM ?? 0, color: '#d69e2e' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            background: 'white', borderRadius: 12, padding: '1rem 1.5rem',
            boxShadow: '0 2px 8px rgba(0,0,0,0.07)', flex: 1, minWidth: 120, textAlign: 'center',
          }}>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, color }}>{value}</div>
            <div style={{ fontSize: '0.8rem', color: '#718096', marginTop: 4 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Embedded report iframe */}
      <div style={{ background: 'white', borderRadius: 12, padding: '1rem', boxShadow: '0 2px 8px rgba(0,0,0,0.07)' }}>
        <iframe
          src={htmlUrl}
          title="Security Report"
          style={{ width: '100%', height: '75vh', border: 'none', borderRadius: 8 }}
        />
      </div>
    </div>
  )
}
