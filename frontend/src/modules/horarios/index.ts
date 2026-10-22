import type { ModuloFrontend } from '../types'

const modulo: ModuloFrontend = {
  nombre: 'horarios',
  etiqueta: 'Horarios',
  icono: 'mdi-calendar-clock',
  orden: 20,
  rutas: [
    { path: 'grilla', etiqueta: 'Horario por curso', component: () => import('./views/Grilla.vue') },
    { path: 'bloques', etiqueta: 'Carga de horarios', component: () => import('./views/Bloques.vue') },
  ],
}

export default modulo
