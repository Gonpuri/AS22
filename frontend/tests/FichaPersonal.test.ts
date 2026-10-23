import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import { http } from '@/api/http'
import { datosPersonales, fecha, filaDesignacion, formatoPad, type Persona } from '@/modules/rrhh/ficha'
import FichaPersonal from '@/modules/rrhh/views/FichaPersonal.vue'

const persona: Persona = {
  id: 5, apellido: 'Iraola', nombre: 'Cecilia', dni: '30123456', cuil: '27-30123456-4', fecha_nacimiento: '1980-05-01',
  domicilio: 'Calle 1 123', telefono: '1122334455', email: 'ci@escuela.edu.ar', fecha_ingreso: '2010-03-01', pad: '12.345', activo: true,
}

describe('helpers de la ficha', () => {
  it('formatea fechas sin corrimientos de zona horaria', () => {
    expect(fecha('1980-05-01')).toBe('01/05/1980')
    expect(fecha(null)).toBe('-')
  })

  it('ordena los datos personales y marca lo que falta con guion', () => {
    const datos = datosPersonales({ ...persona, cuil: '', telefono: '', activo: false })
    expect(datos.map((d) => d.etiqueta)).toEqual([
      'Apellido', 'Nombre', 'DNI', 'CUIL', 'Fecha de nacimiento', 'Domicilio', 'Teléfono', 'Email', 'Fecha de ingreso', 'PAD', 'Activo',
    ])
    expect(Object.fromEntries(datos.map((d) => [d.etiqueta, d.valor]))).toMatchObject({
      DNI: '30123456', CUIL: '-', Teléfono: '-', Activo: 'No', 'Fecha de nacimiento': '01/05/1980', PAD: '12,345',
    })
  })

  it('formatea el PAD en formato local y avisa si falta', () => {
    expect(formatoPad('12.345')).toBe('12,345')
    expect(formatoPad('10.000')).toBe('10')
    expect(formatoPad('1234.5')).toBe('1.234,5')
    expect(formatoPad('0.000')).toBe('0')
    expect(formatoPad(null)).toBe('-')
    expect(formatoPad('')).toBe('-')
  })

  it('traduce categoría, turno y situación de revista', () => {
    expect(filaDesignacion({ id: 1, categoria: 'profesor', turno: 'manana', situacion_revista: 'titular_interino', cargo: '' })).toEqual({
      categoria: 'Profesor', turno: 'Mañana', situacion: 'Titular interino', cargo: '-',
    })
  })
})

describe('Ficha personal', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  async function abrir(id: string) {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/rrhh/personal/:id', component: FichaPersonal }] })
    await router.push(`/rrhh/personal/${id}`)
    await router.isReady()
    const vuetify = createVuetify({ components: componentes, directives: directivas })
    const w = mount(FichaPersonal, { global: { plugins: [vuetify, router] }, attachTo: document.body })
    await flushPromises()
    return w
  }

  it('pide la persona y sus designaciones y muestra los datos personales', async () => {
    const get = vi.spyOn(http, 'get').mockImplementation(async (url: string) =>
      url.includes('/designaciones/')
        ? { data: [{ id: 1, categoria: 'profesor', turno: 'tarde', situacion_revista: 'suplente', cargo: '' }] }
        : { data: persona },
    )
    const w = await abrir('5')
    expect(get).toHaveBeenCalledWith('/api/rrhh/personal/5/')
    expect(get).toHaveBeenCalledWith('/api/rrhh/designaciones/', { params: { personal: '5' } })
    expect(w.find('[data-test="titulo"]').text()).toBe('Iraola, Cecilia')
    const datos = w.find('[data-test="datos"]').text()
    for (const dato of ['30123456', '27-30123456-4', '01/05/1980', '12,345', 'Calle 1 123', '1122334455', 'ci@escuela.edu.ar', '01/03/2010']) {
      expect(datos).toContain(dato)
    }
    const designaciones = w.find('[data-test="designaciones"]').text()
    for (const dato of ['Profesor', 'Tarde', 'Suplente']) expect(designaciones).toContain(dato)
  })

  it('muestra el error si la persona no existe', async () => {
    vi.spyOn(http, 'get').mockRejectedValue({ response: { data: { detail: 'No encontrado.' } } })
    const w = await abrir('999')
    expect(w.find('[data-test="error"]').text()).toContain('No encontrado.')
    expect(w.find('[data-test="titulo"]').exists()).toBe(false)
  })
})
