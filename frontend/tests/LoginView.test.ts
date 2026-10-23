import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as componentes from 'vuetify/components'
import * as directivas from 'vuetify/directives'
import LoginView from '@/components/LoginView.vue'
import { auth } from '@/stores/auth'

async function montar() {
  const vuetify = createVuetify({ components: componentes, directives: directivas })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: { template: '<div />' } }] })
  const Envoltorio = defineComponent({ render: () => h(componentes.VApp, () => h(LoginView)) })
  const w = mount(Envoltorio, { global: { plugins: [vuetify, router] }, attachTo: document.body })
  await flushPromises()
  return w
}

async function enviar(w: Awaited<ReturnType<typeof montar>>, usuario: string, clave: string) {
  const inputs = w.findAll('input')
  await inputs[0].setValue(usuario)
  await inputs[1].setValue(clave)
  await w.find('form').trigger('submit')
  await flushPromises()
}

describe('Login', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('ignora los espacios que el teclado agrega al nombre de usuario, pero no toca la contraseña', async () => {
    const ingresar = vi.spyOn(auth, 'ingresar').mockResolvedValue()
    await enviar(await montar(), 'maria ', ' clave con espacios ')
    expect(ingresar).toHaveBeenCalledWith('maria', ' clave con espacios ')
  })

  it('muestra el error del servidor sin el nombre técnico del campo', async () => {
    vi.spyOn(auth, 'ingresar').mockRejectedValue({
      response: { data: { non_field_errors: ['No puede iniciar sesión con las credenciales proporcionadas.'] } },
    })
    const w = await montar()
    await enviar(w, 'maria', 'mala')
    expect(w.text()).toContain('No puede iniciar sesión con las credenciales proporcionadas.')
    expect(w.text()).not.toContain('non_field_errors')
  })

  it('los campos le indican al navegador que son de inicio de sesión', async () => {
    const w = await montar()
    const [usuario, clave] = w.findAll('input')
    expect(usuario.attributes('autocomplete')).toBe('username')
    expect(clave.attributes('autocomplete')).toBe('current-password')
  })
})
