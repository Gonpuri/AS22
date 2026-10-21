<script setup lang="ts">
import { computed } from 'vue'
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'
import { useOpciones } from '@/api/opciones'
import { CATEGORIAS_DOCENTES } from '../opciones'

const docentes = useOpciones('/api/rrhh/designaciones', (d) => d.etiqueta, {
  filtro: (d) => CATEGORIAS_DOCENTES.includes(d.categoria),
})
const divisiones = useOpciones('/api/academico/divisiones', (d) => d.etiqueta)
const materias = useOpciones('/api/academico/materias', (m) => m.nombre)

const campos = computed<Campo[]>(() => [
  { clave: 'designacion', etiqueta: 'Docente', tipo: 'select', opciones: docentes.value, requerido: true },
  { clave: 'division', etiqueta: 'Curso (división)', tipo: 'select', opciones: divisiones.value, requerido: true },
  { clave: 'materia', etiqueta: 'Materia', tipo: 'select', opciones: materias.value, requerido: true },
])
</script>

<template>
  <CrudView titulo="Cursos y materias de docentes" endpoint="/api/rrhh/asignaciones" :campos="campos" />
</template>
