<script setup lang="ts">
import { computed } from 'vue'
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'
import { useOpciones } from '@/api/opciones'

const anios = useOpciones('/api/academico/anios', (a) => `${a.numero}°`)
const orientaciones = useOpciones('/api/academico/orientaciones', (o) => o.nombre)

const campos = computed<Campo[]>(() => [
  { clave: 'nombre', etiqueta: 'Materia', requerido: true },
  { clave: 'anios', etiqueta: 'Años', tipo: 'multiple', opciones: anios.value },
  { clave: 'orientaciones', etiqueta: 'Orientaciones', tipo: 'multiple', opciones: orientaciones.value },
])
</script>

<template>
  <CrudView titulo="Materias" endpoint="/api/academico/materias" :campos="campos" />
</template>
