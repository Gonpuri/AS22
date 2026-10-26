import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import '@/styles/moderno.css'
import { createVuetify } from 'vuetify'
import { temaGuardado } from '@/stores/tema'

// Paleta fría: azul índigo / cian sobre grises azulados.
const claro = {
  dark: false,
  colors: {
    background: '#F4F7FB',
    surface: '#FFFFFF',
    'surface-variant': '#E6ECF5',
    'on-surface-variant': '#475569',
    primary: '#3B63E0',
    secondary: '#0E9AA7',
    info: '#0EA5E9',
    success: '#10B981',
    warning: '#F59E0B',
    error: '#E5484D',
  },
}

const oscuro = {
  dark: true,
  colors: {
    background: '#0B1220',
    surface: '#131C2E',
    'surface-variant': '#1E2A42',
    'on-surface-variant': '#A9B8D0',
    primary: '#7C9CFF',
    secondary: '#3CC8D6',
    info: '#38BDF8',
    success: '#34D399',
    warning: '#FBBF24',
    error: '#FF7A80',
  },
}

export default createVuetify({
  theme: { defaultTheme: temaGuardado(), themes: { light: claro, dark: oscuro } },
  defaults: {
    VTextField: { variant: 'outlined', density: 'comfortable', rounded: 'lg' },
    VSelect: { variant: 'outlined', density: 'comfortable', rounded: 'lg' },
    VBtn: { rounded: 'lg', elevation: 0, class: 'text-none font-weight-medium' },
    VCard: { rounded: 'xl', elevation: 0, border: true },
    VAlert: { rounded: 'lg' },
    VDataTable: { hover: true },
  },
})
