import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'
import { auth } from '@/stores/auth'

const api = vi.hoisted(() => ({
  listar: vi.fn(),
  crear: vi.fn(),
  actualizar: vi.fn(),
  eliminar: vi.fn(),
}))
vi.mock('@/api/crud', () => ({ crud: () => api }))

const campos: Campo[] = [
  { clave: 'nombre', etiqueta: 'Nombre', requerido: true },
  { clave: 'tipo', etiqueta: 'Tipo', tipo: 'select', opciones: [{ value: 1, title: 'Uno' }] },
  { clave: 'activo', etiqueta: 'Activo', tipo: 'checkbox' },
]

function montar() {
  const vuetify = createVuetify({ components: componentes, directives: directivas })
  return mount(CrudView, {
    props: { titulo: 'Cosas', endpoint: '/api/x', campos },
    global: { plugins: [vuetify] },
    attachTo: document.body,
  })
}

describe('CrudView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = ''
    api.listar.mockResolvedValue([{ id: 1, nombre: 'Alfa', tipo: 1, activo: false }])
    auth.estado.usuario = { id: 1, username: 'a', first_name: '', last_name: '', is_staff: true }
  })

  it('lista los registros traduciendo selects y booleanos', async () => {
    const w = montar()
    await flushPromises()
    expect(w.text()).toContain('Cosas')
    expect(w.text()).toContain('Alfa')
    expect(w.text()).toContain('Uno')
    expect(w.text()).toContain('No')
  })

  it('los campos de solo lectura se ven en la tabla pero no en el formulario', async () => {
    const vuetify = createVuetify({ components: componentes, directives: directivas })
    api.listar.mockResolvedValue([{ id: 1, nombre: 'Alfa', categorias: ['a', 'b'] }])
    const w = mount(CrudView, {
      props: {
        titulo: 'Cosas',
        endpoint: '/api/x',
        campos: [
          { clave: 'nombre', etiqueta: 'Nombre' },
          { clave: 'categorias', etiqueta: 'Categorías', soloLectura: true, formato: (v: string[]) => v.join('+') },
        ],
      },
      global: { plugins: [vuetify] },
      attachTo: document.body,
    })
    await flushPromises()
    expect(w.text()).toContain('a+b')
    await w.find('[data-test="editar"]').trigger('click')
    await flushPromises()
    expect(document.body.querySelector('#form-crud')!.textContent).not.toContain('Categorías')
  })

  it('un usuario común no ve acciones de edición', async () => {
    auth.estado.usuario = { id: 2, username: 'u', first_name: '', last_name: '', is_staff: false }
    const w = montar()
    await flushPromises()
    expect(w.find('[data-test="nuevo"]').exists()).toBe(false)
    expect(w.find('[data-test="editar"]').exists()).toBe(false)
  })

  it('crea un registro nuevo y recarga', async () => {
    api.crear.mockResolvedValue({ id: 2 })
    const w = montar()
    await flushPromises()
    await w.find('[data-test="nuevo"]').trigger('click')
    await flushPromises()
    const etiqueta = [...document.body.querySelectorAll('label')].find((l) => l.htmlFor && l.textContent?.includes('Nombre'))!
    const entrada = document.getElementById(etiqueta.htmlFor) as HTMLInputElement
    entrada.value = 'Beta'
    entrada.dispatchEvent(new Event('input'))
    await flushPromises()
    ;(document.body.querySelector('#form-crud') as HTMLFormElement).dispatchEvent(new Event('submit', { cancelable: true }))
    await flushPromises()
    expect(api.crear).toHaveBeenCalledWith(expect.objectContaining({ nombre: 'Beta', activo: true }))
    expect(api.listar).toHaveBeenCalledTimes(2)
  })

  it('edita un registro existente', async () => {
    api.actualizar.mockResolvedValue({})
    const w = montar()
    await flushPromises()
    await w.find('[data-test="editar"]').trigger('click')
    await flushPromises()
    ;(document.body.querySelector('#form-crud') as HTMLFormElement).dispatchEvent(new Event('submit', { cancelable: true }))
    await flushPromises()
    expect(api.actualizar).toHaveBeenCalledWith(1, expect.objectContaining({ nombre: 'Alfa' }))
  })

  it('elimina tras confirmar y muestra el error del servidor si falla', async () => {
    api.eliminar.mockRejectedValue({ response: { data: { detail: 'No se puede eliminar: hay registros que dependen de este.' } } })
    const w = montar()
    await flushPromises()
    await w.find('[data-test="eliminar"]').trigger('click')
    await flushPromises()
    ;(document.body.querySelector('[data-test="confirmar-eliminar"]') as HTMLElement).click()
    await flushPromises()
    expect(api.eliminar).toHaveBeenCalledWith(1)
    expect(w.text()).toContain('No se puede eliminar')
  })
})
