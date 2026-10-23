export const categorias = [
  { value: 'preceptor', title: 'Preceptor' },
  { value: 'directivo', title: 'Equipo directivo' },
  { value: 'profesor', title: 'Profesor' },
  { value: 'ematp', title: 'EMATP' },
  { value: 'otro', title: 'Otro' },
]

// Los mismos turnos que los de los cursos.
export { turnos } from '../academico/opciones'

export const situacionesRevista = [
  { value: 'titular', title: 'Titular' },
  { value: 'titular_interino', title: 'Titular interino' },
  { value: 'suplente', title: 'Suplente' },
  { value: 'provisional', title: 'Provisional' },
]

/** Categorías que dictan clases: tienen cursos y materias asignados. */
export const CATEGORIAS_DOCENTES = ['profesor', 'ematp']
