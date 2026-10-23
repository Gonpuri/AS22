<script setup lang="ts">
import { computed, ref } from 'vue'
import CrudView from '@/components/CrudView.vue'
import type { Campo, Opcion } from '@/components/campos'
import type { Registro } from '@/api/crud'
import { useOpciones } from '@/api/opciones'
import { CATEGORIAS_DOCENTES, situacionesRevista } from '../opciones'

const docentes = useOpciones('/api/rrhh/designaciones', (d) => d.etiqueta, {
  filtro: (d) => CATEGORIAS_DOCENTES.includes(d.categoria),
})
const divisiones = useOpciones('/api/academico/divisiones', (d) => d.etiqueta)
const materias = useOpciones('/api/academico/materias', (m) => m.nombre)

// Un suplente reemplaza a quien ocupa el cargo (titular, titular interino o provisional) en el mismo curso y materia.
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
  { clave: 'designacion', etiqueta: 'Docente', tipo: 'select', opciones: docentes.value, requerido: true },
  { clave: 'division', etiqueta: 'Curso (división)', tipo: 'select', opciones: divisiones.value, requerido: true },
  { clave: 'materia', etiqueta: 'Materia', tipo: 'select', opciones: materias.value, requerido: true },
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
    titulo="Cursos y materias de docentes"
    endpoint="/api/rrhh/asignaciones"
    :campos="campos"
    @cargado="actualizarReemplazables"
  />
</template>
