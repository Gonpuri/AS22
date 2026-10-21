import type { RouteRecordRaw } from 'vue-router'

/** Contrato de un módulo del frontend: cada carpeta src/modules/<nombre>/index.ts exporta uno por defecto. */
export interface ModuloFrontend {
  nombre: string
  etiqueta: string
  icono: string
  soloAdmin?: boolean
  orden: number
  /** Rutas hijas del layout principal; los paths son relativos (sin barra inicial). */
  rutas: { path: string; etiqueta: string; component: RouteRecordRaw['component'] }[]
}
