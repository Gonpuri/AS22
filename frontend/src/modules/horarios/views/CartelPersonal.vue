<script setup lang="ts">
import { rutaFicha, type LineaDocente, type LineaPad } from '../grilla'

/** `mayorPad` solo se informa en el cartel de una materia: sin él (encabezado) no se muestra esa sección. */
defineProps<{ lineas: LineaDocente[]; vacio: string; mayorPad?: LineaPad[] }>()
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
    <template v-if="mayorPad">
      <v-divider class="my-2" />
      <div class="text-caption text-medium-emphasis" data-test="mayor-pad-titulo">
        Mayor PAD en este horario (responsable ante la falta de autoridades)
      </div>
      <div v-if="!mayorPad.length" class="text-medium-emphasis" data-test="mayor-pad-vacio">
        Sin docentes con PAD cargado en este horario
      </div>
      <div v-for="m in mayorPad" :key="m.personalId" class="persona" data-test="mayor-pad">
        {{ m.puesto }}.
        <router-link :to="rutaFicha(m.personalId)" data-test="responsable">{{ m.nombre }}</router-link>
        <span> — PAD {{ m.pad }}</span>
      </div>
    </template>
  </v-card>
</template>

<style scoped>
.cartel { min-width: 260px; }
.persona + .persona { margin-top: 6px; }
</style>
