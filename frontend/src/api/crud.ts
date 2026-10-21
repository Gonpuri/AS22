import { http } from './http'

export type Registro = Record<string, any> & { id: number }

/** Cliente CRUD genérico. DRF exige barra final en las rutas; FastAPI no. */
export function crud(base: string, barraFinal = true) {
  const url = (id?: number) => `${base}${id !== undefined ? `/${id}` : ''}${barraFinal ? '/' : ''}`
  return {
    listar: async (params?: Record<string, unknown>) => (await http.get<Registro[]>(url(), { params })).data,
    crear: async (datos: object) => (await http.post<Registro>(url(), datos)).data,
    actualizar: async (id: number, datos: object) => (await http.put<Registro>(url(id), datos)).data,
    eliminar: async (id: number) => { await http.delete(url(id)) },
  }
}
