import { categorias, situacionesRevista, turnos } from './opciones'

export interface Persona {
  id: number
  apellido: string
  nombre: string
  dni: string
  cuil: string
  fecha_nacimiento: string | null
  domicilio: string
  telefono: string
  email: string
  fecha_ingreso: string | null
  activo: boolean
}

export interface DesignacionPersona {
  id: number
  categoria: string
  turno: string
  situacion_revista: string
  cargo: string
}

const titulo = (opciones: { value: string; title: string }[], valor: string) =>
  opciones.find((o) => o.value === valor)?.title ?? valor

/** "1980-05-01" -> "01/05/1980" (sin pasar por Date, para evitar corrimientos de zona horaria). */
export function fecha(iso: string | null): string {
  if (!iso) return '-'
  const [a, m, d] = iso.split('-')
  return `${d}/${m}/${a}`
}

const dato = (valor: string) => valor || '-'

/** Datos personales en el orden en que se muestran en la ficha. */
export function datosPersonales(p: Persona): { etiqueta: string; valor: string }[] {
  return [
    { etiqueta: 'Apellido', valor: p.apellido },
    { etiqueta: 'Nombre', valor: p.nombre },
    { etiqueta: 'DNI', valor: p.dni },
    { etiqueta: 'CUIL', valor: dato(p.cuil) },
    { etiqueta: 'Fecha de nacimiento', valor: fecha(p.fecha_nacimiento) },
    { etiqueta: 'Domicilio', valor: dato(p.domicilio) },
    { etiqueta: 'Teléfono', valor: dato(p.telefono) },
    { etiqueta: 'Email', valor: dato(p.email) },
    { etiqueta: 'Fecha de ingreso', valor: fecha(p.fecha_ingreso) },
    { etiqueta: 'Activo', valor: p.activo ? 'Sí' : 'No' },
  ]
}

export const filaDesignacion = (d: DesignacionPersona) => ({
  categoria: titulo(categorias, d.categoria),
  turno: titulo(turnos, d.turno),
  situacion: titulo(situacionesRevista, d.situacion_revista),
  cargo: dato(d.cargo),
})
