import { describe, expect, it } from 'vitest'
import { armarFilas, lineasDocentes, type BloqueGrilla, type Docente } from '@/modules/horarios/grilla'

const bloque = (id: number, dia: number, inicio: string, fin: string, materia: string, docentes: Docente[] = []): BloqueGrilla => ({
  id, dia, hora_inicio: inicio, hora_fin: fin, materia, docentes,
})

describe('armarFilas', () => {
  it('sin bloques no hay filas', () => {
    expect(armarFilas([])).toEqual([])
  })

  it('agrupa por franja horaria y ordena por hora', () => {
    const filas = armarFilas([
      bloque(1, 2, '14:00:00', '15:00:00', 'Inglés'),
      bloque(2, 1, '13:00:00', '14:00:00', 'Matemática'),
      bloque(3, 3, '14:00:00', '15:00:00', 'NTICX'),
      bloque(4, 1, '14:00:00', '15:00:00', 'Matemática'),
    ])
    expect(filas.map((f) => f.etiqueta)).toEqual(['13:00 a 14:00', '14:00 a 15:00'])
    expect(filas[1].celdas[1]?.materia).toBe('Matemática')
    expect(filas[1].celdas[2]?.materia).toBe('Inglés')
    expect(filas[1].celdas[3]?.materia).toBe('NTICX')
    expect(filas[0].celdas[2]).toBeUndefined()
  })

  it('franjas con distinto horario de fin son filas distintas', () => {
    const filas = armarFilas([bloque(1, 1, '15:10:00', '16:10:00', 'Historia'), bloque(2, 2, '15:10:00', '16:00:00', 'Arte')])
    expect(filas.map((f) => f.etiqueta)).toEqual(['15:10 a 16:00', '15:10 a 16:10'])
  })
})

describe('lineasDocentes', () => {
  it('muestra cada docente con su situación de revista', () => {
    const b = bloque(1, 1, '13:00:00', '14:00:00', 'Literatura', [
      { nombre: 'Iraola, Cecilia', situacion_revista: 'Titular' },
      { nombre: 'Ramírez, Priscila', situacion_revista: 'Suplente' },
    ])
    expect(lineasDocentes(b)).toEqual(['Iraola, Cecilia (Titular)', 'Ramírez, Priscila (Suplente)'])
  })

  it('avisa si no hay docente asignado', () => {
    expect(lineasDocentes(bloque(1, 1, '13:00:00', '14:00:00', 'Arte'))).toEqual(['Sin docente asignado'])
  })
})
