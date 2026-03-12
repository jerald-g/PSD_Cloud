import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, register } from '../api.js'

export default function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      if (isRegister) {
        await register(email, password, fullName)
        setSuccess('Account created! You can now sign in.')
        setIsRegister(false)
      } else {
        await login(email, password)
        navigate('/')
      }
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : isRegister ? 'Registration failed' : 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '0.6rem 0.8rem', border: '1px solid #e2e8f0',
    borderRadius: 8, marginBottom: '1rem', fontSize: '0.95rem', boxSizing: 'border-box',
  }
  const labelStyle = { display: 'block', marginBottom: '0.25rem', fontSize: '0.85rem', fontWeight: 600, color: '#4a5568' }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%)',
    }}>
      <div style={{
        background: 'white', borderRadius: 16, padding: '2.5rem', width: 400,
        boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
      }}>
        <h1 style={{ marginBottom: '0.25rem', fontSize: '1.5rem', color: '#1a365d' }}>PSD Cloud</h1>
        <p style={{ marginBottom: '2rem', color: '#718096', fontSize: '0.9rem' }}>
          {isRegister ? 'Create an account' : 'Security Platform'}
        </p>

        {error && (
          <div style={{ background: '#fed7d7', color: '#c53030', padding: '0.75rem', borderRadius: 8, marginBottom: '1rem', fontSize: '0.9rem' }}>
            {error}
          </div>
        )}
        {success && (
          <div style={{ background: '#c6f6d5', color: '#276749', padding: '0.75rem', borderRadius: 8, marginBottom: '1rem', fontSize: '0.9rem' }}>
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {isRegister && (
            <>
              <label style={labelStyle}>Full Name</label>
              <input
                type="text" value={fullName} onChange={e => setFullName(e.target.value)}
                style={inputStyle} placeholder="John Doe"
              />
            </>
          )}

          <label style={labelStyle}>Email</label>
          <input
            type="email" value={email} onChange={e => setEmail(e.target.value)} required
            style={inputStyle} placeholder="you@example.com"
          />

          <label style={labelStyle}>Password</label>
          <input
            type="password" value={password} onChange={e => setPassword(e.target.value)} required
            style={{ ...inputStyle, marginBottom: '1.5rem' }} placeholder="Min 8 characters"
          />

          <button
            type="submit" disabled={loading}
            style={{
              width: '100%', background: '#2b6cb0', color: 'white', border: 'none',
              padding: '0.75rem', borderRadius: 8, fontSize: '1rem', fontWeight: 600, cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? (isRegister ? 'Creating account...' : 'Signing in...') : (isRegister ? 'Create Account' : 'Sign in')}
          </button>
        </form>

        <div style={{ marginTop: '1.25rem', textAlign: 'center', fontSize: '0.9rem', color: '#718096' }}>
          {isRegister ? (
            <>Already have an account?{' '}
              <button onClick={() => { setIsRegister(false); setError(''); setSuccess('') }}
                style={{ background: 'none', border: 'none', color: '#2b6cb0', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem' }}>
                Sign in
              </button>
            </>
          ) : (
            <>Don't have an account?{' '}
              <button onClick={() => { setIsRegister(true); setError(''); setSuccess('') }}
                style={{ background: 'none', border: 'none', color: '#2b6cb0', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem' }}>
                Register
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
