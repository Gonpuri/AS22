<script setup lang="ts">
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'

const campos: Campo[] = [{ clave: 'numero', etiqueta: 'Año', tipo: 'numero', requerido: true }]
</script>

<template>
  <CrudView titulo="Años" endpoint="/api/academico/anios" :campos="campos" />
</template>
