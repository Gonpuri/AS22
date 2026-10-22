import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import { http } from '@/api/http'
import Grilla from '@/modules/horarios/views/Grilla.vue'

const bloque = (id: number, dia: number, inicio: string, fin: string, materia: string) => ({
  id, dia, hora_inicio: inicio, hora_fin: fin, materia, docentes: [],
})

function responder(grilla: object) {
  vi.spyOn(http, 'get').mockImplementation(async (url: string) => {
    if (url.includes('/divisiones')) return { data: [{ id: 7, etiqueta: '4° 1ª' }] }
    if (url.includes('/grilla')) return { data: grilla }
    throw new Error(`URL inesperada: ${url}`)
  })
}

async function montarYElegir() {
  const vuetify = createVuetify({ components: componentes, directives: directivas })
  const w = mount(Grilla, { global: { plugins: [vuetify] }, attachTo: document.body })
  await flushPromises()
  ;(w.vm as unknown as { divisionId: number }).divisionId = 7
  await flushPromises()
  return w
}

describe('Grilla de horarios', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('muestra encabezado, días, franjas y materias como el horario en papel', async () => {
    responder({
      division: { id: 7, anio: 4, nombre: '1ª', orientacion: 'Comunicación' },
      bloques: [bloque(1, 1, '13:00:00', '14:00:00', 'Matemática'), bloque(2, 2, '13:00:00', '14:00:00', 'Inglés')],
    })
    const w = await montarYElegir()
    const texto = w.text()
    expect(texto).toContain('Curso: 4°')
    expect(texto).toContain('División: 1ª')
    expect(texto).toContain('Modalidad: Comunicación')
    expect(texto).toContain('HORARIO')
    for (const dia of ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']) expect(texto).toContain(dia)
    expect(texto).toContain('13:00 a 14:00')
    expect(w.findAll('[data-test="materia"]').map((m) => m.text())).toEqual(['Matemática', 'Inglés'])
    expect(w.find('table').text()).not.toContain('Profesor')
  })

  it('avisa cuando el curso no tiene horarios', async () => {
    responder({ division: { id: 7, anio: 4, nombre: '1ª', orientacion: null }, bloques: [] })
    const w = await montarYElegir()
    expect(w.text()).toContain('todavía no tiene horarios')
    expect(w.text()).not.toContain('Modalidad')
  })

  it('muestra el error del servidor', async () => {
    vi.spyOn(http, 'get').mockImplementation(async (url: string) => {
      if (url.includes('/divisiones')) return { data: [] }
      throw { response: { data: { detail: 'División inexistente.' } } }
    })
    const w = await montarYElegir()
    expect(w.text()).toContain('División inexistente.')
  })
})
