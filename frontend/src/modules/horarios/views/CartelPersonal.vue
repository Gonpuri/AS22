<script setup lang="ts">
import { rutaFicha, type LineaDocente } from '../grilla'

defineProps<{ lineas: LineaDocente[]; vacio: string }>()
</script>

<template>
  <v-card class="pa-3 cartel">
    <div v-if="!lineas.length">{{ vacio }}</div>
    <div v-for="l in lineas" :key="`${l.personalId}-${l.reemplaza?.personalId}`" class="persona">
      <router-link :to="rutaFicha(l.personalId)" data-test="docente">{{ l.nombre }}</router-link>
      <span> ({{ l.situacion }})</span>
      <template v-if="l.reemplaza">
        <span class="text-medium-emphasis"> · suplente de </span>
        <router-link :to="rutaFicha(l.reemplaza.personalId)" data-test="reemplazado">{{ l.reemplaza.nombre }}</router-link>
        <span> ({{ l.reemplaza.situacion }})</span>
      </template>
      <span v-else-if="l.sinTitular" class="text-medium-emphasis"> · sin titular indicado</span>
    </div>
  </v-card>
</template>

<style scoped>
.cartel { min-width: 260px; }
.persona + .persona { margin-top: 6px; }
</style>
