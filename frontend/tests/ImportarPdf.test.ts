import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import { http } from '@/api/http'
import { auth } from '@/stores/auth'
import ImportarPdf from '@/modules/horarios/views/ImportarPdf.vue'

type Vm = { divisionId: number; archivo: File; bloques: { materia: number | null }[]; leer(): Promise<void>; guardar(): Promise<void> }

const propuesta = (materia: number | null) => ({
  division: 7,
  bloques: [
    { dia: 1, hora_inicio: '07:30:00', hora_fin: '08:30:00', materia: 1, texto: 'Matemática' },
    { dia: 2, hora_inicio: '07:30:00', hora_fin: '08:30:00', materia, texto: 'Fisica rara' },
  ],
})

async function montar(respuestaPrevia: object) {
  vi.spyOn(http, 'get').mockImplementation(async (url: string) => ({
    data: url.includes('/divisiones') ? [{ id: 7, etiqueta: '4° 1ª' }] : [{ id: 1, nombre: 'Matemática' }, { id: 2, nombre: 'Inglés' }],
  }))
  const post = vi.spyOn(http, 'post').mockImplementation(async (url: string) => ({
    data: url.endsWith('/previsualizar') ? respuestaPrevia : { creados: 2, existentes: 0, eliminados: 0 },
  }))
  const vuetify = createVuetify({ components: componentes, directives: directivas })
  const w = mount(ImportarPdf, { global: { plugins: [vuetify] }, attachTo: document.body })
  await flushPromises()
  const vm = w.vm as unknown as Vm
  vm.divisionId = 7
  vm.archivo = new File(['%PDF'], 'horario.pdf', { type: 'application/pdf' })
  await flushPromises()
  await vm.leer()
  await flushPromises()
  return { w, vm, post }
}

describe('Carga de horario desde PDF', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
    auth.estado.usuario = { id: 1, username: 'a', first_name: '', last_name: '', is_staff: true }
  })

  it('muestra la propuesta y bloquea el guardado hasta resolver las materias sin reconocer', async () => {
    const { w, vm } = await montar(propuesta(null))
    const enviado = (http.post as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(enviado[0]).toBe('/api/horarios/importar/previsualizar')
    expect((enviado[1] as FormData).get('division')).toBe('7')
    expect(w.find('[data-test="propuesta"]').text()).toContain('Fisica rara')
    expect(w.find('[data-test="faltan"]').exists()).toBe(true)
    expect(w.find('[data-test="guardar"]').attributes('disabled')).toBeDefined()
    vm.bloques[1].materia = 2
    await flushPromises()
    expect(w.find('[data-test="faltan"]').exists()).toBe(false)
    expect(w.find('[data-test="guardar"]').attributes('disabled')).toBeUndefined()
  })

  it('guarda los bloques revisados y avisa el resultado', async () => {
    const { w, vm, post } = await montar(propuesta(2))
    await vm.guardar()
    await flushPromises()
    const [url, cuerpo] = post.mock.calls[1]
    expect(url).toBe('/api/horarios/importar')
    expect(cuerpo).toEqual({
      division: 7,
      reemplazar: false,
      bloques: [
        { dia: 1, hora_inicio: '07:30:00', hora_fin: '08:30:00', materia: 1 },
        { dia: 2, hora_inicio: '07:30:00', hora_fin: '08:30:00', materia: 2 },
      ],
    })
    expect(w.find('[data-test="resultado"]').text()).toContain('2 bloques creados')
  })

  it('los usuarios que no son administradores no ven el formulario', async () => {
    auth.estado.usuario = { id: 2, username: 'b', first_name: '', last_name: '', is_staff: false }
    vi.spyOn(http, 'get').mockResolvedValue({ data: [] })
    const vuetify = createVuetify({ components: componentes, directives: directivas })
    const w = mount(ImportarPdf, { global: { plugins: [vuetify] } })
    await flushPromises()
    expect(w.find('[data-test="solo-admin"]').exists()).toBe(true)
    expect(w.find('[data-test="leer"]').exists()).toBe(false)
  })
})
