<script setup lang="ts">
import { computed } from 'vue'
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'
import { useOpciones } from '@/api/opciones'
import { turnos } from '../opciones'

const anios = useOpciones('/api/academico/anios', (a) => `${a.numero}°`)
const orientaciones = useOpciones('/api/academico/orientaciones', (o) => o.nombre)

const campos = computed<Campo[]>(() => [
  { clave: 'anio', etiqueta: 'Año', tipo: 'select', opciones: anios.value, requerido: true },
  { clave: 'orientacion', etiqueta: 'Orientación', tipo: 'select', opciones: orientaciones.value },
  { clave: 'nombre', etiqueta: 'División', requerido: true },
  { clave: 'turno', etiqueta: 'Turno', tipo: 'select', opciones: turnos, requerido: true },
])
</script>

<template>
  <CrudView titulo="Divisiones" endpoint="/api/academico/divisiones" :campos="campos" />
</template>
