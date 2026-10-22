import { describe, expect, it } from 'vitest'
import { fechaLarga, fechasSinClases, filasDeClases, type DiaConsulta } from '@/modules/consulta_docente/consulta'

const clase = { hora_inicio: '13:00', hora_fin: '14:00', curso: '4° 1ª', materia: 'Matemática', situacion_revista: 'Titular' }
const dias: DiaConsulta[] = [
  { fecha: '2026-10-19', dia: 'Lunes', clases: [clase, { ...clase, hora_inicio: '14:00', hora_fin: '15:00' }] },
  { fecha: '2026-10-20', dia: 'Martes', clases: [] },
  { fecha: '2026-10-24', dia: 'Sábado', clases: [] },
]

describe('consulta de docentes', () => {
  it('formatea la fecha sin corrimientos de zona horaria', () => {
    expect(fechaLarga('2026-10-19')).toBe('19/10/2026')
    expect(fechaLarga('2026-01-01')).toBe('01/01/2026')
  })

  it('una fila por clase con día, fecha, horario y curso', () => {
    expect(filasDeClases(dias)).toEqual([
      { fecha: 'Lunes 19/10/2026', horario: '13:00 a 14:00', curso: '4° 1ª', materia: 'Matemática', situacion_revista: 'Titular' },
      { fecha: 'Lunes 19/10/2026', horario: '14:00 a 15:00', curso: '4° 1ª', materia: 'Matemática', situacion_revista: 'Titular' },
    ])
  })

  it('lista las fechas sin clases', () => {
    expect(fechasSinClases(dias)).toEqual(['Mar 20/10', 'Sáb 24/10'])
  })
})
