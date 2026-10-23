import { computed } from 'vue'
import { useTheme } from 'vuetify'

export type Tema = 'light' | 'dark'

const CLAVE = 'tema'

/** Tema guardado en este navegador (claro si no hay nada o el almacenamiento no está disponible). */
export function temaGuardado(): Tema {
  try {
    return localStorage.getItem(CLAVE) === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

/** Modo claro / oscuro: cambia el tema de Vuetify y recuerda la elección. */
export function useModoOscuro() {
  const theme = useTheme()
  const oscuro = computed(() => theme.global.name.value === 'dark')

  function elegir(esOscuro: boolean | null) {
    const tema: Tema = esOscuro ? 'dark' : 'light'
    theme.global.name.value = tema
    try {
      localStorage.setItem(CLAVE, tema)
    } catch {
      // sin almacenamiento (modo privado): el cambio vale solo para esta sesión
    }
  }

  return { oscuro, elegir }
}
