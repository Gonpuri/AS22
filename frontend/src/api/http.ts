import axios from 'axios'

const CLAVE_TOKEN = 'token'

export const http = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000' })

export const tokenGuardado = () => localStorage.getItem(CLAVE_TOKEN)
export const guardarToken = (t: string | null) =>
  t ? localStorage.setItem(CLAVE_TOKEN, t) : localStorage.removeItem(CLAVE_TOKEN)

http.interceptors.request.use((config) => {
  const token = tokenGuardado()
  if (token) config.headers.Authorization = `Token ${token}`
  return config
})

/** Convierte las respuestas de error de DRF/FastAPI en un texto legible. */
export function mensajeError(e: unknown): string {
  const data = (e as { response?: { data?: unknown } })?.response?.data
  if (!data) return 'No se pudo conectar con el servidor.'
  if (typeof data === 'string') return data
  const d = data as Record<string, unknown>
  if (typeof d.detail === 'string') return d.detail
  if (Array.isArray(d.detail)) return d.detail.map((x) => (x as { msg?: string }).msg ?? String(x)).join(' ')
  return Object.entries(d)
    .map(([campo, msg]) => `${campo}: ${Array.isArray(msg) ? msg.join(' ') : String(msg)}`)
    .join(' · ')
}
