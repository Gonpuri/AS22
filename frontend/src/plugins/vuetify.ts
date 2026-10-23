import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import { temaGuardado } from '@/stores/tema'

export default createVuetify({
  theme: { defaultTheme: temaGuardado() },
  defaults: { VTextField: { variant: 'outlined', density: 'comfortable' }, VSelect: { variant: 'outlined', density: 'comfortable' } },
})
