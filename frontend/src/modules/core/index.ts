import type { ModuloFrontend } from '../types'

const modulo: ModuloFrontend = {
  nombre: 'administracion',
  etiqueta: 'Administración',
  icono: 'mdi-cog',
  soloAdmin: true,
  orden: 100,
  rutas: [{ path: 'usuarios', etiqueta: 'Usuarios', component: () => import('./views/Usuarios.vue') }],
}

export default modulo
