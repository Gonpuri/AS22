export interface Clase {
  hora_inicio: string
  hora_fin: string
  curso: string
  materia: string
  situacion_revista: string
}

export interface DiaConsulta {
  fecha: string
  dia: string
  clases: Clase[]
}

export interface RespuestaConsulta {
  docente: { id: number; apellido: string; nombre: string; cuil: string }
  desde: string
  hasta: string
  cursos_asignados: number
  tiene_clases: boolean
  dias: DiaConsulta[]
}

/** "2026-10-19" -> "19/10/2026" (sin pasar por Date, para evitar corrimientos de zona horaria). */
export function fechaLarga(iso: string): string {
  const [a, m, d] = iso.split('-')
  return `${d}/${m}/${a}`
}

/** Una fila por clase, con el día y la fecha, para mostrar en tabla. */
export function filasDeClases(dias: DiaConsulta[]) {
  return dias.flatMap((d) =>
    d.clases.map((c) => ({
      fecha: `${d.dia} ${fechaLarga(d.fecha)}`,
      horario: `${c.hora_inicio} a ${c.hora_fin}`,
      curso: c.curso,
      materia: c.materia,
      situacion_revista: c.situacion_revista,
    })),
  )
}

/** Fechas del intervalo en las que el docente no tiene clases. */
export const fechasSinClases = (dias: DiaConsulta[]) =>
  dias.filter((d) => !d.clases.length).map((d) => `${d.dia.slice(0, 3)} ${fechaLarga(d.fecha).slice(0, 5)}`)
