import type { ModuloFrontend } from '../types'

const modulo: ModuloFrontend = {
  nombre: 'consulta_docente',
  etiqueta: 'Consulta de docentes',
  icono: 'mdi-account-search',
  orden: 25,
  rutas: [{ path: 'clases', etiqueta: 'Clases por fecha', component: () => import('./views/ClasesDocente.vue') }],
}

export default modulo
