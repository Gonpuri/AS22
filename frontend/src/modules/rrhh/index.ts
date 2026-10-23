import type { ModuloFrontend } from '../types'

const modulo: ModuloFrontend = {
  nombre: 'rrhh',
  etiqueta: 'Recursos humanos',
  icono: 'mdi-account-group',
  orden: 30,
  rutas: [
    { path: 'personal', etiqueta: 'Personal', component: () => import('./views/Personal.vue') },
    { path: 'personal/:id', etiqueta: 'Ficha personal', component: () => import('./views/FichaPersonal.vue'), oculta: true },
    { path: 'designaciones', etiqueta: 'Designaciones', component: () => import('./views/Designaciones.vue') },
    { path: 'preceptores', etiqueta: 'Preceptores por curso', component: () => import('./views/Preceptores.vue') },
    { path: 'asignaciones', etiqueta: 'Cursos y materias', component: () => import('./views/Asignaciones.vue') },
  ],
}

export default modulo
