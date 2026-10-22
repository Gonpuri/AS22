import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { guardarToken, http, mensajeError, reintentos, tokenGuardado } from '@/api/http'
import { crud } from '@/api/crud'

describe('mensajeError', () => {
  const err = (data: unknown) => ({ response: { data } })

  it('sin respuesta del servidor', () => {
    expect(mensajeError(new Error('x'))).toContain('No se pudo conectar con el servidor')
    expect(mensajeError(new Error('x'))).toContain(String(http.defaults.baseURL))
  })
  it('detail de DRF/FastAPI', () => {
    expect(mensajeError(err({ detail: 'No permitido.' }))).toBe('No permitido.')
  })
  it('errores de validación de FastAPI (lista)', () => {
    expect(mensajeError(err({ detail: [{ msg: 'campo requerido' }] }))).toBe('campo requerido')
  })
  it('errores por campo de DRF', () => {
    expect(mensajeError(err({ nombre: ['Ya existe.'], anio: ['Requerido.'] }))).toBe('nombre: Ya existe. · anio: Requerido.')
  })
})

describe('token', () => {
  beforeEach(() => localStorage.clear())

  it('se guarda, se envía en cada pedido y se borra', async () => {
    guardarToken('abc')
    expect(tokenGuardado()).toBe('abc')
    const config = await (http.interceptors.request as any).handlers[0].fulfilled({ headers: {} })
    expect(config.headers.Authorization).toBe('Token abc')
    guardarToken(null)
    expect(tokenGuardado()).toBeNull()
  })
})

describe('crud', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('usa barra final para DRF', async () => {
    const get = vi.spyOn(http, 'get').mockResolvedValue({ data: [{ id: 1 }] })
    const put = vi.spyOn(http, 'put').mockResolvedValue({ data: {} })
    const del = vi.spyOn(http, 'delete').mockResolvedValue({})
    const post = vi.spyOn(http, 'post').mockResolvedValue({ data: {} })
    const api = crud('/api/academico/anios')
    expect(await api.listar()).toEqual([{ id: 1 }])
    await api.crear({ numero: 1 })
    await api.actualizar(3, { numero: 2 })
    await api.eliminar(3)
    expect(get).toHaveBeenCalledWith('/api/academico/anios/', { params: undefined })
    expect(post).toHaveBeenCalledWith('/api/academico/anios/', { numero: 1 })
    expect(put).toHaveBeenCalledWith('/api/academico/anios/3/', { numero: 2 })
    expect(del).toHaveBeenCalledWith('/api/academico/anios/3/')
  })

  it('sin barra final para FastAPI', async () => {
    const put = vi.spyOn(http, 'put').mockResolvedValue({ data: {} })
    await crud('/api/horarios/bloques', false).actualizar(5, {})
    expect(put).toHaveBeenCalledWith('/api/horarios/bloques/5', {})
  })
})

describe('reintentos mientras la API despierta', () => {
  const original = { ...reintentos }
  const adaptador = (fallos: number, llamadas: string[]) => async (config: any) => {
    llamadas.push(`${config.method} ${config.url}`)
    if (llamadas.length <= fallos) throw Object.assign(new Error('Network Error'), { config, isAxiosError: true })
    return { data: [], status: 200, statusText: 'OK', headers: {}, config }
  }

  beforeEach(() => {
    reintentos.esperaMs = 0
    reintentos.maximo = 3
  })
  afterEach(() => Object.assign(reintentos, original))

  it('reintenta una lectura que falla por red y termina bien', async () => {
    const llamadas: string[] = []
    const r = await http.get('/api/academico/anios/', { adapter: adaptador(2, llamadas) })
    expect(r.status).toBe(200)
    expect(llamadas).toHaveLength(3)
  })

  it('reintenta el login', async () => {
    const llamadas: string[] = []
    await http.post('/api/auth/login/', {}, { adapter: adaptador(1, llamadas) })
    expect(llamadas).toHaveLength(2)
  })

  it('no reintenta altas ni cambios (podrían duplicarse)', async () => {
    const llamadas: string[] = []
    await expect(http.post('/api/academico/orientaciones/', {}, { adapter: adaptador(5, llamadas) })).rejects.toThrow()
    expect(llamadas).toHaveLength(1)
  })

  it('se rinde tras el máximo de intentos', async () => {
    const llamadas: string[] = []
    await expect(http.get('/api/x/', { adapter: adaptador(99, llamadas) })).rejects.toThrow()
    expect(llamadas).toHaveLength(4)
  })

  it('no reintenta si el servidor respondió con error', async () => {
    const llamadas: string[] = []
    const adapter = async (config: any) => {
      llamadas.push('x')
      throw Object.assign(new Error('403'), { config, isAxiosError: true, response: { status: 403, data: {} } })
    }
    await expect(http.get('/api/x/', { adapter })).rejects.toThrow()
    expect(llamadas).toHaveLength(1)
  })
})
