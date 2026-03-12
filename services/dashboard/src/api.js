import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_URL || ''

const client = axios.create({ baseURL: BASE })

// Attach JWT from localStorage on every request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('psd_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redirect to login on 401 (expired/invalid token)
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config.url?.includes('/auth/')) {
      localStorage.removeItem('psd_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth
export const register = (email, password, fullName) =>
  client.post('/api/auth/register', { email, password, full_name: fullName })

export const login = async (email, password) => {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  const { data } = await client.post('/api/auth/token', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  localStorage.setItem('psd_token', data.access_token)
  return data
}

export const logout = () => localStorage.removeItem('psd_token')

export const getMe = () => client.get('/api/auth/me')

// Scans
export const listScans = (limit = 50, offset = 0) =>
  client.get('/api/scans', { params: { limit, offset } })

export const getScan = (id) => client.get(`/api/scans/${id}`)

export const createScan = (payload) => client.post('/api/scans', payload)

// Reports
export const getReportHtmlUrl = (scanId) => `${BASE}/api/reports/${scanId}/html`
export const getReportJsonUrl = (scanId) => `${BASE}/api/reports/${scanId}/json`
export const getReportPdfUrl = (scanId) => `${BASE}/api/reports/${scanId}/pdf`
