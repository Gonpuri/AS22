import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'
import { auth } from '@/stores/auth'
import { crud } from '@/api/crud'

const api = vi.hoisted(() => ({
  listar: vi.fn(),
  crear: vi.fn(),
  actualizar: vi.fn(),
  eliminar: vi.fn(),
}))
vi.mock('@/api/crud', () => ({ crud: vi.fn(() => api) }))

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

  it('usa barra final en las URLs por defecto (DRF) y no la usa si se indica (FastAPI)', async () => {
    const vuetify = createVuetify({ components: componentes, directives: directivas })
    const props = { titulo: 'Cosas', endpoint: '/api/x', campos }
    mount(CrudView, { props, global: { plugins: [vuetify] } })
    expect(crud).toHaveBeenLastCalledWith('/api/x', true)
    mount(CrudView, { props: { ...props, barraFinal: false }, global: { plugins: [vuetify] } })
    expect(crud).toHaveBeenLastCalledWith('/api/x', false)
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

  it('al crear, los textos opcionales sin completar se envían vacíos (no null) y respeta porDefecto', async () => {
    api.crear.mockResolvedValue({ id: 3 })
    const vuetify = createVuetify({ components: componentes, directives: directivas })
    const w = mount(CrudView, {
      props: {
        titulo: 'Usuarios',
        endpoint: '/api/x',
        campos: [
          { clave: 'username', etiqueta: 'Usuario', requerido: true },
          { clave: 'first_name', etiqueta: 'Nombre' },
          { clave: 'email', etiqueta: 'Email', tipo: 'email' },
          { clave: 'password', etiqueta: 'Contraseña', tipo: 'password', requerido: true },
          { clave: 'is_staff', etiqueta: 'Administrador', tipo: 'checkbox', porDefecto: false },
          { clave: 'is_active', etiqueta: 'Activo', tipo: 'checkbox' },
        ],
      },
      global: { plugins: [vuetify] },
      attachTo: document.body,
    })
    await flushPromises()
    await w.find('[data-test="nuevo"]').trigger('click')
    await flushPromises()
    const escribir = async (etiqueta: string, valor: string) => {
      const l = [...document.body.querySelectorAll('label')].find((x) => x.htmlFor && x.textContent?.includes(etiqueta))!
      const input = document.getElementById(l.htmlFor) as HTMLInputElement
      input.value = valor
      input.dispatchEvent(new Event('input'))
    }
    await escribir('Usuario', 'maria')
    await escribir('Contraseña', 'Clave-Segura-123')
    await flushPromises()
    ;(document.body.querySelector('#form-crud') as HTMLFormElement).dispatchEvent(new Event('submit', { cancelable: true }))
    await flushPromises()
    expect(api.crear).toHaveBeenCalledWith({
      username: 'maria', first_name: '', email: '', password: 'Clave-Segura-123', is_staff: false, is_active: true,
    })
    const clave = [...document.body.querySelectorAll('input')].find((i) => i.type === 'password')!
    expect(clave.getAttribute('autocomplete')).toBe('new-password') // evita que el navegador complete la clave guardada
  })

  it('los campos numéricos admiten decimales y, si se borran, se envían como sin valor (null)', async () => {
    api.crear.mockResolvedValue({ id: 4 })
    const vuetify = createVuetify({ components: componentes, directives: directivas })
    const w = mount(CrudView, {
      props: {
        titulo: 'Personal',
        endpoint: '/api/x',
        campos: [
          { clave: 'nombre', etiqueta: 'Nombre' },
          { clave: 'pad', etiqueta: 'PAD', tipo: 'numero' },
          { clave: 'nacimiento', etiqueta: 'Nacimiento', tipo: 'fecha' },
        ],
      },
      global: { plugins: [vuetify] },
      attachTo: document.body,
    })
    await flushPromises()
    await w.find('[data-test="nuevo"]').trigger('click')
    await flushPromises()
    const campo = (etiqueta: string) => {
      const l = [...document.body.querySelectorAll('label')].find((x) => x.htmlFor && x.textContent?.includes(etiqueta))!
      return document.getElementById(l.htmlFor) as HTMLInputElement
    }
    const pad = campo('PAD')
    expect(pad.getAttribute('step')).toBe('any') // sin esto el navegador rechaza 12,5 al enviar
    for (const valor of ['12.5', '']) {
      pad.value = valor
      pad.dispatchEvent(new Event('input'))
    }
    const nacimiento = campo('Nacimiento')
    nacimiento.value = '1980-05-01'
    nacimiento.dispatchEvent(new Event('input'))
    nacimiento.value = ''
    nacimiento.dispatchEvent(new Event('input'))
    await flushPromises()
    ;(document.body.querySelector('#form-crud') as HTMLFormElement).dispatchEvent(new Event('submit', { cancelable: true }))
    await flushPromises()
    expect(api.crear).toHaveBeenCalledWith({ nombre: '', pad: null, nacimiento: null })
  })
})
