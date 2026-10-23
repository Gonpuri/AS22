import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import { http } from '@/api/http'
import { lineasPersonal, nombresEncabezado, type Docente } from '@/modules/horarios/grilla'
import Grilla from '@/modules/horarios/views/Grilla.vue'

const titular: Docente = {
  personal_id: 10, nombre: 'Furchs, Marcela', situacion_revista: 'Titular', es_suplente: false, suplente_de: null,
}
const suplente: Docente = {
  personal_id: 11, nombre: 'Zárate, Laura', situacion_revista: 'Suplente', es_suplente: true,
  suplente_de: { personal_id: 10, nombre: 'Furchs, Marcela', situacion_revista: 'Titular' },
}

describe('preceptores en el encabezado: lógica', () => {
  it('muestra a quienes ocupan el cargo; si solo hay suplentes, a los suplentes', () => {
    expect(nombresEncabezado([titular, suplente])).toBe('Furchs, Marcela')
    expect(nombresEncabezado([suplente])).toBe('Zárate, Laura')
    expect(nombresEncabezado([titular, { ...titular, personal_id: 12, nombre: 'Gómez, Ana' }])).toBe('Furchs, Marcela / Gómez, Ana')
    expect(nombresEncabezado([])).toBe('')
  })

  it('el preceptor suplente indica a quién reemplaza, igual que un profesor', () => {
    expect(lineasPersonal([titular, suplente])[1]).toEqual({
      personalId: 11, nombre: 'Zárate, Laura', situacion: 'Suplente', sinTitular: false,
      reemplaza: { personalId: 10, nombre: 'Furchs, Marcela', situacion: 'Titular' },
    })
  })
})

async function montar(preceptores?: Docente[]) {
  vi.spyOn(http, 'get').mockImplementation(async (url: string) => {
    if (url.includes('/divisiones')) return { data: [{ id: 7, etiqueta: '4° 1ª' }] }
    return {
      data: {
        division: { id: 7, anio: 4, nombre: '1ª', orientacion: 'Comunicación' },
        ...(preceptores ? { preceptores } : {}),
        bloques: [],
      },
    }
  })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pagina(.*)*', component: { template: '<div />' } }] })
  const vuetify = createVuetify({ components: componentes, directives: directivas })
  const w = mount(Grilla, { global: { plugins: [vuetify, router] }, attachTo: document.body })
  await flushPromises()
  ;(w.vm as unknown as { divisionId: number }).divisionId = 7
  await flushPromises()
  return { w, router }
}

describe('Planilla por curso: preceptor', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('figura en el encabezado junto a curso, división y modalidad', async () => {
    const { w } = await montar([titular, suplente])
    const encabezado = w.find('.encabezado').text()
    expect(encabezado).toContain('Curso: 4°')
    expect(encabezado).toContain('Modalidad: Comunicación')
    expect(encabezado).toContain('Preceptor/a: Furchs, Marcela')
    expect(encabezado).not.toContain('Zárate') // el suplente aparece en el cartel
  })

  it('al abrirlo muestra situación de revista, suplente de quién y enlaces a las fichas', async () => {
    const { w } = await montar([titular, suplente])
    await w.find('[data-test="preceptor-nombre"]').trigger('click')
    await flushPromises()
    const cartel = document.body.querySelector('[data-test="preceptores"]')!
    expect(cartel.textContent).toContain('Furchs, Marcela (Titular)')
    expect(cartel.textContent).toMatch(/Zárate, Laura \(Suplente\)\s*· suplente de\s*Furchs, Marcela \(Titular\)/)
    const enlaces = [...cartel.querySelectorAll<HTMLAnchorElement>('a')].map((a) => a.getAttribute('href'))
    expect(enlaces).toEqual(['/rrhh/personal/10', '/rrhh/personal/11', '/rrhh/personal/10'])
  })

  it('al hacer clic en el preceptor navega a su ficha personal', async () => {
    const { w, router } = await montar([titular])
    await w.find('[data-test="preceptor-nombre"]').trigger('click')
    await flushPromises()
    document.body.querySelector('[data-test="preceptores"] [data-test="docente"]')!
      .dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }))
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/rrhh/personal/10'))
  })

  it('sin preceptor asignado lo indica', async () => {
    const { w } = await montar([])
    expect(w.find('[data-test="preceptor"]').text()).toBe('Preceptor/a: sin asignar')
  })

  it('tolera una API que todavía no envía preceptores', async () => {
    const { w } = await montar(undefined)
    expect(w.find('[data-test="preceptor"]').text()).toContain('sin asignar')
  })
})
