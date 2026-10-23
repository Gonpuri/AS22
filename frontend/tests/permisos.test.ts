import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import AppLayout from '@/components/AppLayout.vue'
import { primeraRuta, router } from '@/router'
import { auth } from '@/stores/auth'

type Rol = 'staff' | 'superusuario' | 'comun'
const ROLES: Record<Rol, { is_staff: boolean; is_superuser: boolean }> = {
  staff: { is_staff: true, is_superuser: false },
  superusuario: { is_staff: false, is_superuser: true },
  comun: { is_staff: false, is_superuser: false },
}

function entrarComo(rol: Rol) {
  auth.estado.token = 'token-de-prueba'
  auth.estado.usuario = { id: 1, username: 'u', first_name: '', last_name: '', ...ROLES[rol] }
}

describe('esAdmin', () => {
  it('staff y superusuario son administradores; el usuario común no', () => {
    entrarComo('staff')
    expect(auth.esAdmin.value).toBe(true)
    entrarComo('superusuario')
    expect(auth.esAdmin.value).toBe(true)
    entrarComo('comun')
    expect(auth.esAdmin.value).toBe(false)
    auth.estado.usuario = null
    expect(auth.esAdmin.value).toBe(false)
  })
})

describe('rutas protegidas', () => {
  beforeEach(() => entrarComo('comun'))

  it('la pantalla de inicio de un usuario común es Horarios, no una sección restringida', () => {
    expect(primeraRuta()).toBe('/horarios/grilla')
    entrarComo('staff')
    expect(primeraRuta()).toBe('/academico/orientaciones')
  })

  it.each(['/academico/orientaciones', '/academico/anios', '/academico/divisiones', '/academico/materias', '/administracion/usuarios'])(
    'un usuario común que escribe %s en la barra de direcciones vuelve al inicio',
    async (ruta) => {
      entrarComo('comun')
      await router.push(ruta)
      expect(router.currentRoute.value.fullPath).toBe('/horarios/grilla')
    },
  )

  it('el usuario común sí entra a Horarios, Recursos humanos y Consulta de docentes', async () => {
    for (const ruta of ['/horarios/grilla', '/horarios/bloques', '/rrhh/personal', '/consulta_docente/clases']) {
      await router.push(ruta)
      expect(router.currentRoute.value.fullPath).toBe(ruta)
    }
  })

  it('la raíz no entra en un bucle de redirecciones para el usuario común', async () => {
    await router.push('/')
    expect(router.currentRoute.value.fullPath).toBe('/horarios/grilla')
  })

  it.each<Rol>(['staff', 'superusuario'])('%s entra a Estructura académica y Administración', async (rol) => {
    entrarComo(rol)
    for (const ruta of ['/academico/materias', '/administracion/usuarios']) {
      await router.push(ruta)
      expect(router.currentRoute.value.fullPath).toBe(ruta)
    }
  })

  it('sin sesión va al login', async () => {
    auth.estado.token = null
    await router.push('/academico/materias')
    expect(router.currentRoute.value.fullPath).toBe('/login')
  })
})

describe('menú lateral', () => {
  async function menuDe(rol: Rol) {
    entrarComo(rol)
    const vuetify = createVuetify({ components: componentes, directives: directivas })
    const Envoltorio = defineComponent({ render: () => h(componentes.VApp, () => h(AppLayout)) })
    const w = mount(Envoltorio, { global: { plugins: [vuetify, router] }, attachTo: document.body })
    await flushPromises()
    return w.find('.v-navigation-drawer').text()
  }

  it('el usuario común no ve Estructura académica ni Administración', async () => {
    const menu = await menuDe('comun')
    expect(menu).not.toContain('Estructura académica')
    expect(menu).not.toContain('Administración')
    for (const visible of ['Horarios', 'Recursos humanos', 'Consulta de docentes']) expect(menu).toContain(visible)
  })

  it.each<Rol>(['staff', 'superusuario'])('%s ve todo el menú', async (rol) => {
    const menu = await menuDe(rol)
    for (const visible of ['Estructura académica', 'Administración', 'Horarios', 'Recursos humanos']) expect(menu).toContain(visible)
  })
})
