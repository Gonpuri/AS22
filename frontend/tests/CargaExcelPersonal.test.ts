import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import { http } from '@/api/http'
import { auth } from '@/stores/auth'
import Personal from '@/modules/rrhh/views/Personal.vue'

const fila = (n: number, dni: string, accion: string, extra: object = {}) => ({
  fila: n, dni, datos: { apellido: 'Pérez', nombre: 'Juan', ...extra }, accion, errores: accion === 'error' ? ['Falta el DNI.'] : [], cambios: [],
})

async function montar() {
  const get = vi.spyOn(http, 'get').mockResolvedValue({ data: [] })
  const post = vi.spyOn(http, 'post').mockImplementation(async (url: string) => ({
    data: url.endsWith('/previsualizar/')
      ? { filas: [fila(2, '30123456', 'crear'), fila(3, '28999888', 'actualizar'), fila(4, '', 'error')] }
      : { creados: 1, actualizados: 1, sin_cambios: 0 },
  }))
  const vuetify = createVuetify({ components: componentes, directives: directivas })
  const w = mount(Personal, { global: { plugins: [vuetify] }, attachTo: document.body })
  await flushPromises()
  return { w, get, post }
}

const dialogo = () => document.body.querySelector('.v-dialog') as HTMLElement | null

describe('Carga de personal desde Excel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
    auth.estado.usuario = { id: 1, username: 'a', first_name: '', last_name: '', is_staff: true }
  })

  it('el botón "Carga Excel" va debajo de "Nuevo", solo para administradores', async () => {
    const { w } = await montar()
    const botones = w.findAll('button').map((b) => b.text())
    expect(botones.indexOf('Carga Excel')).toBe(botones.indexOf('Nuevo') + 1)
    auth.estado.usuario = { id: 2, username: 'b', first_name: '', last_name: '', is_staff: false }
    await flushPromises()
    expect(w.find('[data-test="carga-excel"]').exists()).toBe(false)
  })

  it('lee la planilla, muestra la propuesta y guarda solo las filas sin error', async () => {
    const { w, get, post } = await montar()
    await w.find('[data-test="carga-excel"]').trigger('click')
    await flushPromises()
    expect(dialogo()).not.toBeNull()
    const carga = w.findComponent({ name: 'CargaExcelPersonal' })
    ;(carga.vm as unknown as { archivo: File }).archivo = new File(['x'], 'personal.xlsx')
    await flushPromises()
    await (carga.vm as unknown as { leer(): Promise<void> }).leer()
    await flushPromises()
    expect(dialogo()!.textContent).toContain('1 nuevas · 1 existentes · 1 con error')
    const llamadasGet = get.mock.calls.length
    await (carga.vm as unknown as { guardar(): Promise<void> }).guardar()
    await flushPromises()
    const [url, cuerpo] = post.mock.calls[1] as [string, { filas: { dni: string }[] }]
    expect(url).toBe('/api/rrhh/personal/importar-excel/')
    expect(cuerpo.filas.map((f) => f.dni)).toEqual(['30123456', '28999888'])
    expect(dialogo()!.textContent).toContain('1 personas nuevas, 1 actualizadas')
    expect(get.mock.calls.length).toBeGreaterThan(llamadasGet) // la lista se recarga
  })
})
