import { beforeEach, describe, expect, it, vi } from 'vitest'
import { guardarToken, http, mensajeError, tokenGuardado } from '@/api/http'
import { crud } from '@/api/crud'

describe('mensajeError', () => {
  const err = (data: unknown) => ({ response: { data } })

  it('sin respuesta del servidor', () => {
    expect(mensajeError(new Error('x'))).toBe('No se pudo conectar con el servidor.')
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
