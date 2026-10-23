import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import { http } from '@/api/http'
import Grilla from '@/modules/horarios/views/Grilla.vue'

const titular = {
  personal_id: 1, nombre: 'Iraola, Cecilia', situacion_revista: 'Titular interino', es_suplente: false, suplente_de: null,
}
const suplente = {
  personal_id: 2, nombre: 'Ramírez, Priscila', situacion_revista: 'Suplente', es_suplente: true,
  suplente_de: { personal_id: 1, nombre: 'Iraola, Cecilia', situacion_revista: 'Titular interino' },
}

async function abrirMateria(docentes: object[]) {
  vi.spyOn(http, 'get').mockImplementation(async (url: string) => {
    if (url.includes('/divisiones')) return { data: [{ id: 7, etiqueta: '4° 1ª' }] }
    return {
      data: {
        division: { id: 7, anio: 4, nombre: '1ª', orientacion: null },
        bloques: [{ id: 1, dia: 1, hora_inicio: '13:00:00', hora_fin: '14:00:00', materia: 'Literatura', docentes }],
      },
    }
  })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pagina(.*)*', component: { template: '<div />' } }] })
  const vuetify = createVuetify({ components: componentes, directives: directivas })
  const w = mount(Grilla, { global: { plugins: [vuetify, router] }, attachTo: document.body })
  await flushPromises()
  ;(w.vm as unknown as { divisionId: number }).divisionId = 7
  await flushPromises()
  await w.find('[data-test="materia"]').trigger('click') // el menú también se abre al pasar el puntero
  await flushPromises()
  return { w, router }
}

describe('Cartel de docentes del horario', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('muestra al titular y al suplente indicando a quién reemplaza', async () => {
    await abrirMateria([titular, suplente])
    const cartel = document.body.querySelector('[data-test="docentes"]')!
    expect(cartel.textContent).toContain('Iraola, Cecilia (Titular interino)')
    expect(cartel.textContent).toContain('Ramírez, Priscila (Suplente)')
    expect(cartel.textContent).toContain('suplente de')
    expect(cartel.textContent).toMatch(/suplente de\s*Iraola, Cecilia \(Titular interino\)/)
  })

  it('cada nombre es un enlace a los datos personales del docente', async () => {
    await abrirMateria([titular, suplente])
    const enlaces = [...document.body.querySelectorAll<HTMLAnchorElement>('[data-test="docentes"] a')]
    expect(enlaces.map((a) => [a.textContent, a.getAttribute('href')])).toEqual([
      ['Iraola, Cecilia', '/rrhh/personal/1'],
      ['Ramírez, Priscila', '/rrhh/personal/2'],
      ['Iraola, Cecilia', '/rrhh/personal/1'], // el reemplazado también lleva a su ficha
    ])
    expect(document.body.querySelector('[data-test="reemplazado"]')?.getAttribute('href')).toBe('/rrhh/personal/1')
  })

  it('al hacer clic en un nombre navega a la ficha', async () => {
    const { router } = await abrirMateria([titular])
    const enlace = document.body.querySelector<HTMLAnchorElement>('[data-test="docente"]')!
    enlace.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }))
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/rrhh/personal/1'))
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/rrhh/personal/1')
  })

  it('un suplente sin titular indicado se marca como tal', async () => {
    await abrirMateria([{ ...suplente, suplente_de: null }])
    expect(document.body.querySelector('[data-test="docentes"]')!.textContent).toContain('sin titular indicado')
  })

  it('sin docentes lo avisa', async () => {
    await abrirMateria([])
    expect(document.body.querySelector('[data-test="docentes"]')!.textContent).toContain('Sin docente asignado')
  })
})
