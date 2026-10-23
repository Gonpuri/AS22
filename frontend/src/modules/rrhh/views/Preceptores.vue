<script setup lang="ts">
import { computed, ref } from 'vue'
import CrudView from '@/components/CrudView.vue'
import type { Campo, Opcion } from '@/components/campos'
import type { Registro } from '@/api/crud'
import { useOpciones } from '@/api/opciones'
import { situacionesRevista } from '../opciones'

const preceptores = useOpciones('/api/rrhh/designaciones', (d) => d.etiqueta, {
  filtro: (d) => d.categoria === 'preceptor',
})
const divisiones = useOpciones('/api/academico/divisiones', (d) => d.etiqueta)

// Un suplente reemplaza a quien ocupa el cargo (titular, titular interino o provisional) en el mismo curso.
const reemplazables = ref<Opcion[]>([])
function actualizarReemplazables(asignaciones: Registro[]) {
  reemplazables.value = asignaciones
    .filter((a) => a.situacion_revista !== 'suplente')
    .map((a) => ({
      value: a.id,
      title: `${a.etiqueta} [${situacionesRevista.find((s) => s.value === a.situacion_revista)?.title}]`,
    }))
}

const campos = computed<Campo[]>(() => [
  { clave: 'designacion', etiqueta: 'Preceptor', tipo: 'select', opciones: preceptores.value, requerido: true },
  { clave: 'division', etiqueta: 'Curso (división)', tipo: 'select', opciones: divisiones.value, requerido: true },
  {
    clave: 'suplente_de',
    etiqueta: 'Suplente de (solo si es suplente)',
    tipo: 'select',
    opciones: reemplazables.value,
    formato: (valor) => (valor ? (reemplazables.value.find((o) => o.value === valor)?.title ?? '') : '-'),
  },
])
</script>

<template>
  <CrudView
    titulo="Preceptores por curso"
    endpoint="/api/rrhh/preceptores"
    :campos="campos"
    @cargado="actualizarReemplazables"
  />
</template>
