import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { auth } from '@/stores/auth'
import { modulos } from '@/modules'
import AppLayout from '@/components/AppLayout.vue'
import LoginView from '@/components/LoginView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { publica: true } },
    {
      path: '/',
      component: AppLayout,
      redirect: () => `/${modulos[0].nombre}/${modulos[0].rutas[0].path}`,
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
