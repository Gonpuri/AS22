<script setup lang="ts">
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'

const campos: Campo[] = [{ clave: 'nombre', etiqueta: 'Nombre', requerido: true }]
</script>

<template>
  <CrudView titulo="Orientaciones" endpoint="/api/academico/orientaciones" :campos="campos" />
</template>
