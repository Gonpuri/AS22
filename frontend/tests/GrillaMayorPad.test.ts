import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import { http } from '@/api/http'
import { lineasMayorPad, type BloqueGrilla } from '@/modules/horarios/grilla'
import Grilla from '@/modules/horarios/views/Grilla.vue'

const bloque = (mayor_pad?: BloqueGrilla['mayor_pad']): BloqueGrilla => ({
  id: 1, dia: 1, hora_inicio: '13:00:00', hora_fin: '14:00:00', materia: 'Matemática', docentes: [], mayor_pad,
})

describe('lineasMayorPad', () => {
  it('numera de mayor a menor y da formato local al PAD', () => {
    const lineas = lineasMayorPad(bloque([
      { personal_id: 3, nombre: 'Alta, Ana', pad: '1234.500' },
      { personal_id: 1, nombre: 'Media, Eva', pad: '20.000' },
      { personal_id: 2, nombre: 'Baja, Lía', pad: '0.250' },
    ]))
    expect(lineas).toEqual([
      { puesto: 1, personalId: 3, nombre: 'Alta, Ana', pad: '1.234,5' },
      { puesto: 2, personalId: 1, nombre: 'Media, Eva', pad: '20' },
      { puesto: 3, personalId: 2, nombre: 'Baja, Lía', pad: '0,25' },
    ])
  })

  it('tolera una API que todavía no envía el dato', () => {
    expect(lineasMayorPad(bloque(undefined))).toEqual([])
  })
})

async function abrirMateria(mayor_pad?: BloqueGrilla['mayor_pad']) {
  vi.spyOn(http, 'get').mockImplementation(async (url: string) => {
    if (url.includes('/divisiones')) return { data: [{ id: 7, etiqueta: '4° 1ª' }] }
    return { data: { division: { id: 7, anio: 4, nombre: '1ª', turno: 'Tarde', orientacion: null }, bloques: [bloque(mayor_pad)] } }
  })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: { template: '<div />' } }] })
  const vuetify = createVuetify({ components: componentes, directives: directivas })
  const w = mount(Grilla, { global: { plugins: [vuetify, router] }, attachTo: document.body })
  await flushPromises()
  ;(w.vm as unknown as { divisionId: number }).divisionId = 7
  await flushPromises()
  await w.find('[data-test="materia"]').trigger('click')
  await flushPromises()
  return document.body.querySelector('[data-test="docentes"]')!
}

describe('Cartel de la materia: mayor PAD del horario', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('lista los tres con mayor PAD, con su puntaje y enlace a la ficha', async () => {
    const cartel = await abrirMateria([
      { personal_id: 3, nombre: 'Alta, Ana', pad: '30.125' },
      { personal_id: 1, nombre: 'Media, Eva', pad: '20.000' },
      { personal_id: 2, nombre: 'Baja, Lía', pad: '10.500' },
    ])
    expect(cartel.querySelector('[data-test="mayor-pad-titulo"]')!.textContent).toContain('Mayor PAD en este horario')
    expect(cartel.querySelector('[data-test="mayor-pad-titulo"]')!.textContent).toContain('falta de autoridades')
    const filas = [...cartel.querySelectorAll('[data-test="mayor-pad"]')].map((f) => f.textContent!.replace(/\s+/g, ' ').trim())
    expect(filas).toEqual([
      '1. Alta, Ana — PAD 30,125',
      '2. Media, Eva — PAD 20',
      '3. Baja, Lía — PAD 10,5',
    ])
    const enlaces = [...cartel.querySelectorAll<HTMLAnchorElement>('[data-test="responsable"]')].map((a) => a.getAttribute('href'))
    expect(enlaces).toEqual(['/rrhh/personal/3', '/rrhh/personal/1', '/rrhh/personal/2'])
  })

  it('con menos de tres muestra solo los que hay', async () => {
    const cartel = await abrirMateria([{ personal_id: 9, nombre: 'Unica, Ana', pad: '5.000' }])
    expect(cartel.querySelectorAll('[data-test="mayor-pad"]')).toHaveLength(1)
  })

  it('si nadie tiene PAD cargado en ese horario, lo avisa', async () => {
    const cartel = await abrirMateria([])
    expect(cartel.querySelector('[data-test="mayor-pad-vacio"]')!.textContent).toContain('Sin docentes con PAD cargado')
  })

  it('el encabezado del preceptor no muestra esa sección', async () => {
    const { default: CartelPersonal } = await import('@/modules/horarios/views/CartelPersonal.vue')
    const vuetify = createVuetify({ components: componentes, directives: directivas })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: { template: '<div />' } }] })
    const w = mount(CartelPersonal, { props: { lineas: [], vacio: '' }, global: { plugins: [vuetify, router] } })
    expect(w.find('[data-test="mayor-pad-titulo"]').exists()).toBe(false)
  })
})
