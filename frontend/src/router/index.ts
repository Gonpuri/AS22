import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { auth } from '@/stores/auth'
import { modulos } from '@/modules'
import AppLayout from '@/components/AppLayout.vue'
import LoginView from '@/components/LoginView.vue'

/** Primera pantalla a la que puede entrar el usuario (los módulos solo para administradores se saltean). */
export function primeraRuta(): string {
  const modulo = modulos.find((m) => !m.soloAdmin || auth.esAdmin.value) ?? modulos[0]
  return `/${modulo.nombre}/${modulo.rutas[0].path}`
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { publica: true } },
    {
      path: '/',
      component: AppLayout,
      redirect: () => primeraRuta(),
      children: modulos.flatMap((m) =>
        m.rutas.map((r) => ({
          path: `${m.nombre}/${r.path}`,
          component: r.component,
          meta: { soloAdmin: m.soloAdmin },
        }) as RouteRecordRaw),
      ),
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.publica) return true
  if (!auth.autenticado.value) return '/login'
  if (!auth.estado.usuario) await auth.cargarUsuario()
  if (!auth.autenticado.value) return '/login'
  if (to.meta.soloAdmin && !auth.esAdmin.value) return '/'
  return true
})
