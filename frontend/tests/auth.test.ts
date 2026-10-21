import { beforeEach, describe, expect, it, vi } from 'vitest'
import { http, tokenGuardado } from '@/api/http'
import { auth } from '@/stores/auth'

describe('auth', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    auth.salir()
  })

  it('ingresar guarda el token y carga el usuario', async () => {
    vi.spyOn(http, 'post').mockResolvedValue({ data: { token: 'tk' } })
    vi.spyOn(http, 'get').mockResolvedValue({ data: { id: 1, username: 'admin', is_staff: true } })
    await auth.ingresar('admin', 'x')
    expect(auth.autenticado.value).toBe(true)
    expect(auth.esAdmin.value).toBe(true)
    expect(tokenGuardado()).toBe('tk')
  })

  it('un usuario común no es administrador', async () => {
    vi.spyOn(http, 'post').mockResolvedValue({ data: { token: 'tk' } })
    vi.spyOn(http, 'get').mockResolvedValue({ data: { id: 2, username: 'u', is_staff: false } })
    await auth.ingresar('u', 'x')
    expect(auth.esAdmin.value).toBe(false)
  })

  it('credenciales incorrectas no dejan sesión', async () => {
    vi.spyOn(http, 'post').mockRejectedValue(new Error('400'))
    await expect(auth.ingresar('a', 'b')).rejects.toThrow()
    expect(auth.autenticado.value).toBe(false)
  })

  it('si el token ya no sirve, cierra la sesión', async () => {
    auth.estado.token = 'viejo'
    vi.spyOn(http, 'get').mockRejectedValue(new Error('401'))
    await auth.cargarUsuario()
    expect(auth.autenticado.value).toBe(false)
  })

  it('salir limpia todo', () => {
    auth.estado.token = 'x'
    auth.salir()
    expect(auth.estado.token).toBeNull()
    expect(tokenGuardado()).toBeNull()
  })
})
