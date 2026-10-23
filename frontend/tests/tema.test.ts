import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import AppLayout from '@/components/AppLayout.vue'
import { auth } from '@/stores/auth'
import { temaGuardado } from '@/stores/tema'

async function montarLayout(tema: 'light' | 'dark' = 'light') {
  const vuetify = createVuetify({ components: componentes, directives: directivas, theme: { defaultTheme: tema } })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: { template: '<div />' } }] })
  const Envoltorio = defineComponent({ render: () => h(componentes.VApp, () => h(AppLayout)) })
  const w = mount(Envoltorio, { global: { plugins: [vuetify, router] }, attachTo: document.body })
  await flushPromises()
  return { w, vuetify }
}

describe('modo claro / oscuro', () => {
  beforeEach(() => {
    localStorage.clear()
    document.body.innerHTML = ''
    auth.estado.usuario = { id: 1, username: 'admin', first_name: '', last_name: '', is_staff: true }
  })

  it('la palanca está en la barra superior', async () => {
    const { w } = await montarLayout()
    expect(w.find('.v-toolbar [data-test="tema"]').exists()).toBe(true)
  })

  it('cambia a oscuro y vuelve a claro, recordando la elección', async () => {
    const { w, vuetify } = await montarLayout()
    const palanca = () => w.find('[data-test="tema"] input')
    expect(vuetify.theme.global.name.value).toBe('light')

    await palanca().setValue(true)
    expect(vuetify.theme.global.name.value).toBe('dark')
    expect(localStorage.getItem('tema')).toBe('dark')
    expect(temaGuardado()).toBe('dark')

    await palanca().setValue(false)
    expect(vuetify.theme.global.name.value).toBe('light')
    expect(localStorage.getItem('tema')).toBe('light')
  })

  it('arranca en oscuro con la palanca activada si así estaba guardado', async () => {
    localStorage.setItem('tema', 'dark')
    const { w, vuetify } = await montarLayout(temaGuardado())
    expect(vuetify.theme.global.name.value).toBe('dark')
    expect((w.find('[data-test="tema"] input').element as HTMLInputElement).checked).toBe(true)
  })
})

describe('temaGuardado', () => {
  beforeEach(() => localStorage.clear())

  it('claro por defecto y ante valores desconocidos', () => {
    expect(temaGuardado()).toBe('light')
    localStorage.setItem('tema', 'violeta')
    expect(temaGuardado()).toBe('light')
  })

  it('claro si el almacenamiento del navegador no está disponible', () => {
    const espia = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('bloqueado')
    })
    expect(temaGuardado()).toBe('light')
    espia.mockRestore()
  })
})
