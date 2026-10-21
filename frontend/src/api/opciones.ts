import { onMounted, ref } from 'vue'
import { crud, type Registro } from './crud'
import type { Opcion } from '@/components/campos'

/** Carga las opciones de un select a partir de un recurso del backend (opcionalmente filtradas). */
export function useOpciones(
  endpoint: string,
  titulo: (r: Registro) => string,
  { barraFinal = true, filtro = () => true }: { barraFinal?: boolean; filtro?: (r: Registro) => boolean } = {},
) {
  const opciones = ref<Opcion[]>([])
  onMounted(async () => {
    const filas = await crud(endpoint, barraFinal).listar()
    opciones.value = filas.filter(filtro).map((r) => ({ value: r.id, title: titulo(r) }))
  })
  return opciones
}
