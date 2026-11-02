import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import { http } from '@/api/http'
import { auth } from '@/stores/auth'
import ImportarPdfCursos from '@/modules/horarios/views/ImportarPdfCursos.vue'

type Vm = { archivo: File; leer(): Promise<void>; guardar(): Promise<void>; cursos: { incluir: boolean; pagina: number }[] }

const curso = (division: string) => ({
  anio: 4, division, turno: 'tarde', modalidad: 'Comunicación', preceptor: 'X', division_id: null, advertencias: [],
  bloques: [{ dia: 1, hora_inicio: '13:00:00', hora_fin: '14:00:00', materia: null, materia_nombre: 'Biología' }],
})

async function montar(leer: (pagina: number) => object) {
  vi.spyOn(http, 'get').mockResolvedValue({ data: [{ id: 1, nombre: 'Matemática' }] })
  const post = vi.spyOn(http, 'post').mockImplementation(async (url: string, cuerpo: unknown) => {
    if (url.endsWith('/pdf/leer')) return { data: leer(Number((cuerpo as FormData).get('pagina'))) }
    return { data: { creados: 2, existentes: 0, eliminados: 0, divisiones_creadas: 2, materias_creadas: 1 } }
  })
  const vuetify = createVuetify({ components: componentes, directives: directivas })
  const w = mount(ImportarPdfCursos, { global: { plugins: [vuetify] }, attachTo: document.body })
  await flushPromises()
  const vm = w.vm as unknown as Vm
  vm.archivo = new File(['%PDF'], 'superior.pdf', { type: 'application/pdf' })
  await flushPromises()
  await vm.leer()
  await flushPromises()
  return { w, vm, post }
}

describe('Carga de cursos desde PDF escaneado', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
    auth.estado.usuario = { id: 1, username: 'a', first_name: '', last_name: '', is_staff: true }
  })

  it('lee una página por vez y muestra un curso por página', async () => {
    const { w, post } = await montar((p) => ({ paginas: 3, pagina: p, curso: curso(`${p}ª`) }))
    expect(post.mock.calls.map((c) => (c[1] as FormData).get('pagina'))).toEqual(['1', '2', '3'])
    expect(w.findAll('[data-test="curso"]')).toHaveLength(3)
    expect(w.find('[data-test="progreso"]').text()).toContain('3 de 3')
  })

  it('si una página falla sigue con las demás y avisa', async () => {
    const { w } = await montar((p) => {
      if (p === 2) throw { response: { data: { detail: 'La IA no pudo leer esta página.' } } }
      return { paginas: 3, pagina: p, curso: curso(`${p}ª`) }
    })
    expect(w.findAll('[data-test="curso"]')).toHaveLength(2)
    expect(w.find('[data-test="error-pagina"]').text()).toContain('Página 2')
  })

  it('guarda solo los cursos tildados con sus materias', async () => {
    const { w, vm, post } = await montar((p) => ({ paginas: 2, pagina: p, curso: curso(`${p}ª`) }))
    vm.cursos[1].incluir = false
    await flushPromises()
    await vm.guardar()
    await flushPromises()
    const [url, cuerpo] = post.mock.calls[2] as [string, { cursos: { division: string; reemplazar: boolean }[] }]
    expect(url).toBe('/api/horarios/importar/cursos')
    expect(cuerpo.cursos.map((c) => c.division)).toEqual(['1ª'])
    expect(w.find('[data-test="resultado"]').text()).toContain('2 bloques en 1 cursos')
  })

  it('los usuarios que no son administradores no ven el formulario', async () => {
    auth.estado.usuario = { id: 2, username: 'b', first_name: '', last_name: '', is_staff: false }
    vi.spyOn(http, 'get').mockResolvedValue({ data: [] })
    const vuetify = createVuetify({ components: componentes, directives: directivas })
    const w = mount(ImportarPdfCursos, { global: { plugins: [vuetify] } })
    await flushPromises()
    expect(w.find('[data-test="solo-admin"]').exists()).toBe(true)
    expect(w.find('[data-test="leer"]').exists()).toBe(false)
  })
})
