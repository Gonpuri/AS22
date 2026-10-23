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

/**
 * El plan gratuito de Render duerme la API tras un rato sin uso: mientras despierta (hasta ~1 minuto)
 * responde sin cabeceras CORS y el navegador lo informa como error de red. Se reintentan las lecturas
 * (GET) y el login, que no modifican datos, en vez de fallar de inmediato.
 */
export const reintentos = { maximo: 8, esperaMs: 8000 }

const sePuedeReintentar = (config: { method?: string; url?: string }) =>
  config.method?.toLowerCase() === 'get' || config.url === '/api/auth/login/'

http.interceptors.response.use(undefined, async (error) => {
  const config = error?.config as (typeof error.config & { _intentos?: number }) | undefined
  if (error?.response || !config || !sePuedeReintentar(config)) throw error
  config._intentos = (config._intentos ?? 0) + 1
  if (config._intentos > reintentos.maximo) throw error
  await new Promise((r) => setTimeout(r, reintentos.esperaMs))
  return http(config)
})

/** Convierte las respuestas de error de DRF/FastAPI en un texto legible. */
export function mensajeError(e: unknown): string {
  const data = (e as { response?: { data?: unknown } })?.response?.data
  if (!data) return `No se pudo conectar con el servidor (${http.defaults.baseURL}). Si la API estaba inactiva, esperá un minuto y reintentá.`
  if (typeof data === 'string') return data
  const d = data as Record<string, unknown>
  if (typeof d.detail === 'string') return d.detail
  if (Array.isArray(d.detail)) return d.detail.map((x) => (x as { msg?: string }).msg ?? String(x)).join(' ')
  return Object.entries(d)
    .map(([campo, msg]) => {
      const texto = Array.isArray(msg) ? msg.join(' ') : String(msg)
      return campo === 'non_field_errors' ? texto : `${campo}: ${texto}`
    })
    .join(' · ')
}
