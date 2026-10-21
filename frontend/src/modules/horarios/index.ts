import type { ModuloFrontend } from '../types'

const modulo: ModuloFrontend = {
  nombre: 'horarios',
  etiqueta: 'Horarios',
  icono: 'mdi-calendar-clock',
  orden: 20,
  rutas: [{ path: 'bloques', etiqueta: 'Horarios', component: () => import('./views/Bloques.vue') }],
}

export default modulo
