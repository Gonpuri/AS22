export interface Docente {
  nombre: string
  situacion_revista: string
}

export interface BloqueGrilla {
  id: number
  dia: number
  hora_inicio: string
  hora_fin: string
  materia: string
  docentes: Docente[]
}

export interface Fila {
  inicio: string
  fin: string
  etiqueta: string
  celdas: Record<number, BloqueGrilla | undefined>
}

export const DIAS = [
  { numero: 1, nombre: 'Lunes' },
  { numero: 2, nombre: 'Martes' },
  { numero: 3, nombre: 'Miércoles' },
  { numero: 4, nombre: 'Jueves' },
  { numero: 5, nombre: 'Viernes' },
]

const hhmm = (hora: string) => hora.slice(0, 5)

/** Una fila por franja horaria distinta (ordenadas por hora), con el bloque de cada día. */
export function armarFilas(bloques: BloqueGrilla[]): Fila[] {
  const filas = new Map<string, Fila>()
  for (const b of bloques) {
    const clave = `${hhmm(b.hora_inicio)}-${hhmm(b.hora_fin)}`
    if (!filas.has(clave)) {
      filas.set(clave, {
        inicio: hhmm(b.hora_inicio),
        fin: hhmm(b.hora_fin),
        etiqueta: `${hhmm(b.hora_inicio)} a ${hhmm(b.hora_fin)}`,
        celdas: {},
      })
    }
    filas.get(clave)!.celdas[b.dia] = b
  }
  return [...filas.values()].sort((a, b) => a.inicio.localeCompare(b.inicio) || a.fin.localeCompare(b.fin))
}

/** Líneas del cartel que aparece al pasar el puntero sobre una materia. */
export function lineasDocentes(bloque: BloqueGrilla): string[] {
  if (!bloque.docentes.length) return ['Sin docente asignado']
  return bloque.docentes.map((d) => `${d.nombre} (${d.situacion_revista})`)
}
