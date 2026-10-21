import type { ModuloFrontend } from '../types'

const modulo: ModuloFrontend = {
  nombre: 'academico',
  etiqueta: 'Estructura académica',
  icono: 'mdi-school',
  orden: 10,
  rutas: [
    { path: 'orientaciones', etiqueta: 'Orientaciones', component: () => import('./views/Orientaciones.vue') },
    { path: 'anios', etiqueta: 'Años', component: () => import('./views/Anios.vue') },
    { path: 'divisiones', etiqueta: 'Divisiones', component: () => import('./views/Divisiones.vue') },
    { path: 'materias', etiqueta: 'Materias', component: () => import('./views/Materias.vue') },
  ],
}

export default modulo
