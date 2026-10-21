import type { ModuloFrontend } from './types'

// Descubre automáticamente cada src/modules/*/index.ts: un módulo nuevo no requiere tocar este archivo.
const encontrados = import.meta.glob<{ default: ModuloFrontend }>('./*/index.ts', { eager: true })

export const modulos: ModuloFrontend[] = Object.values(encontrados)
  .map((m) => m.default)
  .sort((a, b) => a.orden - b.orden)
