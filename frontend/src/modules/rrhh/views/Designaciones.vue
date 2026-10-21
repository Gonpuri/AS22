<script setup lang="ts">
import { computed } from 'vue'
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'
import { useOpciones } from '@/api/opciones'
import { categorias, situacionesRevista, turnos } from '../opciones'

const personal = useOpciones('/api/rrhh/personal', (p) => `${p.apellido}, ${p.nombre}`)

const campos = computed<Campo[]>(() => [
  { clave: 'personal', etiqueta: 'Persona', tipo: 'select', opciones: personal.value, requerido: true },
  { clave: 'categoria', etiqueta: 'Categoría', tipo: 'select', opciones: categorias, requerido: true },
  { clave: 'turno', etiqueta: 'Turno', tipo: 'select', opciones: turnos, requerido: true },
  { clave: 'situacion_revista', etiqueta: 'Situación de revista', tipo: 'select', opciones: situacionesRevista, requerido: true },
  { clave: 'cargo', etiqueta: 'Cargo / función' },
])
</script>

<template>
  <CrudView titulo="Designaciones (categoría y turno)" endpoint="/api/rrhh/designaciones" :campos="campos" />
</template>
