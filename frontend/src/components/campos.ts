import type { Registro } from '@/api/crud'

export interface Opcion { value: number | string; title: string }

export interface Campo {
  clave: string
  etiqueta: string
  tipo?: 'texto' | 'numero' | 'email' | 'password' | 'fecha' | 'hora' | 'checkbox' | 'select' | 'multiple'
  opciones?: Opcion[]
  requerido?: boolean
  /** Texto a mostrar en la tabla (por defecto el valor, o el título de la opción). */
  formato?: (valor: any, fila: Registro) => string
  /** No se muestra en la tabla. */
  soloFormulario?: boolean
  /** Dato calculado por el servidor: se muestra en la tabla pero no está en el formulario. */
  soloLectura?: boolean
}
