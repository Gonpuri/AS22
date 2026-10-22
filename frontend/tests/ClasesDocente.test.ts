import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import { http } from '@/api/http'
import ClasesDocente from '@/modules/consulta_docente/views/ClasesDocente.vue'

const docente = { id: 1, apellido: 'Nievas', nombre: 'Silvia', cuil: '20-30123456-7' }
const clase = { hora_inicio: '13:00', hora_fin: '14:00', curso: '4° 1ª', materia: 'Matemática', situacion_revista: 'Titular' }

async function consultar(valores: { cuil: string; desde: string; hasta?: string }) {
  const vuetify = createVuetify({ components: componentes, directives: directivas })
  const w = mount(ClasesDocente, { global: { plugins: [vuetify] }, attachTo: document.body })
  const escribir = async (test: string, valor: string) => {
    const input = w.find(`[data-test="${test}"] input`)
    await input.setValue(valor)
  }
  await escribir('cuil', valores.cuil)
  await escribir('desde', valores.desde)
  if (valores.hasta) await escribir('hasta', valores.hasta)
  await w.find('form').trigger('submit')
  await flushPromises()
  return w
}

describe('Clases de un docente por fecha', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('envía CUIL y fechas, y muestra curso, horario y materia', async () => {
    const get = vi.spyOn(http, 'get').mockResolvedValue({
      data: {
        docente, desde: '2026-10-19', hasta: '2026-10-20', cursos_asignados: 1, tiene_clases: true,
        dias: [
          { fecha: '2026-10-19', dia: 'Lunes', clases: [clase] },
          { fecha: '2026-10-20', dia: 'Martes', clases: [] },
        ],
      },
    })
    const w = await consultar({ cuil: '20-30123456-7', desde: '2026-10-19', hasta: '2026-10-20' })
    expect(get).toHaveBeenCalledWith('/api/consulta_docente/', {
      params: { cuil: '20-30123456-7', desde: '2026-10-19', hasta: '2026-10-20' },
    })
    expect(w.find('[data-test="resumen"]').text()).toContain('Nievas, Silvia tiene clases entre el 19/10/2026 y el 20/10/2026')
    const tabla = w.find('[data-test="tabla"]').text()
    for (const dato of ['Lunes 19/10/2026', '13:00 a 14:00', '4° 1ª', 'Matemática', 'Titular']) expect(tabla).toContain(dato)
    expect(w.find('[data-test="sin-clases"]').text()).toContain('Mar 20/10')
  })

  it('un solo día: no envía "hasta" y lo dice en el resumen', async () => {
    const get = vi.spyOn(http, 'get').mockResolvedValue({
      data: { docente, desde: '2026-10-20', hasta: '2026-10-20', cursos_asignados: 1, tiene_clases: false,
        dias: [{ fecha: '2026-10-20', dia: 'Martes', clases: [] }] },
    })
    const w = await consultar({ cuil: '20301234567', desde: '2026-10-20' })
    expect(get).toHaveBeenCalledWith('/api/consulta_docente/', { params: { cuil: '20301234567', desde: '2026-10-20' } })
    expect(w.find('[data-test="resumen"]').text()).toContain('no tiene clases el 20/10/2026')
    expect(w.find('[data-test="tabla"]').exists()).toBe(false)
  })

  it('docente sin cursos asignados', async () => {
    vi.spyOn(http, 'get').mockResolvedValue({
      data: { docente, desde: '2026-10-20', hasta: '2026-10-20', cursos_asignados: 0, tiene_clases: false, dias: [] },
    })
    const w = await consultar({ cuil: '20301234567', desde: '2026-10-20' })
    expect(w.find('[data-test="resumen"]').text()).toContain('no tiene cursos ni materias asignados')
  })

  it('muestra el error del servidor (CUIL inexistente)', async () => {
    vi.spyOn(http, 'get').mockRejectedValue({ response: { data: { detail: 'No hay personal registrado con ese CUIL.' } } })
    const w = await consultar({ cuil: '20999999999', desde: '2026-10-20' })
    expect(w.find('[data-test="error"]').text()).toContain('No hay personal registrado con ese CUIL.')
    expect(w.find('[data-test="resumen"]').exists()).toBe(false)
  })
})
