<script setup lang="ts">
import { computed } from 'vue'
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'
import { useOpciones } from '@/api/opciones'

const divisiones = useOpciones('/api/academico/divisiones', (d) => d.etiqueta)
const materias = useOpciones('/api/academico/materias', (m) => m.nombre)
const dias = [
  { value: 1, title: 'Lunes' },
  { value: 2, title: 'Martes' },
  { value: 3, title: 'Miércoles' },
  { value: 4, title: 'Jueves' },
  { value: 5, title: 'Viernes' },
]

const campos = computed<Campo[]>(() => [
  { clave: 'division', etiqueta: 'División', tipo: 'select', opciones: divisiones.value, requerido: true },
  { clave: 'dia', etiqueta: 'Día', tipo: 'select', opciones: dias, requerido: true },
  { clave: 'hora_inicio', etiqueta: 'Desde', tipo: 'hora', requerido: true },
  { clave: 'hora_fin', etiqueta: 'Hasta', tipo: 'hora', requerido: true },
  { clave: 'materia', etiqueta: 'Materia', tipo: 'select', opciones: materias.value, requerido: true },
])
</script>

<template>
  <CrudView titulo="Horarios" endpoint="/api/horarios/bloques" :barra-final="false" :campos="campos" />
</template>
