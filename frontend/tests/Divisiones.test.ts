import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import { http } from '@/api/http'
import { auth } from '@/stores/auth'
import Divisiones from '@/modules/academico/views/Divisiones.vue'

describe('Divisiones: turno', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
    auth.estado.usuario = { id: 1, username: 'a', first_name: '', last_name: '', is_staff: true }
  })

  async function montar() {
    vi.spyOn(http, 'get').mockImplementation(async (url: string) => {
      if (url.includes('/anios')) return { data: [{ id: 1, numero: 1 }] }
      if (url.includes('/orientaciones')) return { data: [] }
      return { data: [{ id: 5, anio: 1, orientacion: null, nombre: '2ª', turno: 'manana', etiqueta: '1° 2ª' }] }
    })
    const vuetify = createVuetify({ components: componentes, directives: directivas })
    const w = mount(Divisiones, { global: { plugins: [vuetify] }, attachTo: document.body })
    await flushPromises()
    return w
  }

  it('la tabla muestra el turno de cada curso con su nombre', async () => {
    const w = await montar()
    expect(w.text()).toContain('Turno')
    expect(w.text()).toContain('Mañana')
  })

  it('el formulario pide el turno como dato obligatorio', async () => {
    const w = await montar()
    await w.find('[data-test="nuevo"]').trigger('click')
    await flushPromises()
    const etiquetas = [...document.body.querySelectorAll('#form-crud label')].map((l) => l.textContent)
    expect(etiquetas.some((t) => t?.includes('Turno *'))).toBe(true)
  })
})
