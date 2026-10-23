import { describe, expect, it } from 'vitest'
import { modulos } from '@/modules'

describe('registro de módulos', () => {
  it('descubre los módulos implementados, ordenados', () => {
    expect(modulos.map((m) => m.nombre)).toEqual(['academico', 'horarios', 'consulta_docente', 'rrhh', 'administracion'])
  })

  it('la administración es solo para administradores', () => {
    expect(modulos.filter((m) => m.soloAdmin).map((m) => m.nombre)).toEqual(['administracion'])
  })

  it('estructura académica expone orientaciones, años, divisiones y materias', () => {
    const academico = modulos.find((m) => m.nombre === 'academico')!
    expect(academico.rutas.map((r) => r.path)).toEqual(['orientaciones', 'anios', 'divisiones', 'materias'])
  })

  it('horarios expone la grilla por curso y la carga de bloques', () => {
    const horarios = modulos.find((m) => m.nombre === 'horarios')!
    expect(horarios.rutas.map((r) => r.path)).toEqual(['grilla', 'bloques'])
  })

  it('consulta de docentes expone las clases por fecha', () => {
    const consulta = modulos.find((m) => m.nombre === 'consulta_docente')!
    expect(consulta.rutas.map((r) => r.path)).toEqual(['clases'])
  })

  it('RR. HH. expone personal, designaciones y cursos/materias de docentes', () => {
    const rrhh = modulos.find((m) => m.nombre === 'rrhh')!
    expect(rrhh.rutas.map((r) => r.path)).toEqual(['personal', 'personal/:id', 'designaciones', 'asignaciones'])
  })

  it('la ficha personal existe como ruta pero no aparece en el menú', () => {
    const ficha = modulos.find((m) => m.nombre === 'rrhh')!.rutas.find((r) => r.path === 'personal/:id')!
    expect(ficha.oculta).toBe(true)
    expect(modulos.flatMap((m) => m.rutas).filter((r) => r.oculta)).toHaveLength(1)
  })

  it('cada ruta tiene componente', () => {
    for (const m of modulos) for (const r of m.rutas) expect(r.component).toBeTruthy()
  })
})
