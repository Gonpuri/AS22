import { reactive, computed } from 'vue'
import { http, guardarToken, tokenGuardado } from '@/api/http'

interface Usuario { id: number; username: string; first_name: string; last_name: string; is_staff: boolean; is_superuser?: boolean }

const estado = reactive<{ token: string | null; usuario: Usuario | null }>({
  token: tokenGuardado(),
  usuario: null,
})

export const auth = {
  estado,
  autenticado: computed(() => !!estado.token),
  /** Administrador: staff o superusuario (igual que en el servidor). */
  esAdmin: computed(() => !!(estado.usuario?.is_staff || estado.usuario?.is_superuser)),

  async ingresar(username: string, password: string) {
    const { data } = await http.post<{ token: string }>('/api/auth/login/', { username, password })
    estado.token = data.token
    guardarToken(data.token)
    await auth.cargarUsuario()
  },

  async cargarUsuario() {
    if (!estado.token) return
    try {
      estado.usuario = (await http.get<Usuario>('/api/auth/yo/')).data
    } catch {
      auth.salir()
    }
  },

  salir() {
    estado.token = null
    estado.usuario = null
    guardarToken(null)
  },
}
