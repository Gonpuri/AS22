<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { http, mensajeError } from '@/api/http'
import { useOpciones } from '@/api/opciones'
import {
  armarFilas, DIAS, lineasDocentes, lineasPersonal, nombresEncabezado, type BloqueGrilla, type Docente,
} from '../grilla'
import CartelPersonal from './CartelPersonal.vue'

interface Grilla {
  division: { id: number; anio: number; nombre: string; turno?: string; orientacion: string | null }
  preceptores?: Docente[] // ausente si la API aún no se actualizó
  bloques: BloqueGrilla[]
}

const divisiones = useOpciones('/api/academico/divisiones', (d) => d.etiqueta)
const divisionId = ref<number | null>(null)
const grilla = ref<Grilla | null>(null)
const error = ref('')

const filas = computed(() => armarFilas(grilla.value?.bloques ?? []))
const preceptores = computed(() => grilla.value?.preceptores ?? [])

watch(divisionId, async (id) => {
  grilla.value = null
  error.value = ''
  if (id === null) return
  try {
    grilla.value = (await http.get<Grilla>('/api/horarios/grilla', { params: { division: id } })).data
  } catch (e) {
    error.value = mensajeError(e)
  }
})
</script>

<template>
  <div>
    <h2 class="text-h5 mb-4">Horario por curso</h2>
    <v-select
      v-model="divisionId"
      :items="divisiones"
      label="Curso y división"
      style="max-width: 320px"
      data-test="division"
    />
    <v-alert v-if="error" type="error" class="mb-4">{{ error }}</v-alert>

    <div v-if="grilla" class="horario">
      <div class="encabezado">
        <span>Curso: <b>{{ grilla.division.anio }}°</b></span>
        <span>División: <b>{{ grilla.division.nombre }}</b></span>
        <span v-if="grilla.division.turno" data-test="turno">Turno: <b>{{ grilla.division.turno }}</b></span>
        <span v-if="grilla.division.orientacion">Modalidad: <b>{{ grilla.division.orientacion }}</b></span>
        <span data-test="preceptor">
          Preceptor/a:
          <v-menu v-if="preceptores.length" open-on-hover open-on-click :close-delay="200" location="bottom">
            <template #activator="{ props }">
              <b v-bind="props" class="preceptor-nombre" data-test="preceptor-nombre">{{ nombresEncabezado(preceptores) }}</b>
            </template>
            <CartelPersonal :lineas="lineasPersonal(preceptores)" vacio="" data-test="preceptores" />
          </v-menu>
          <span v-else class="text-medium-emphasis">sin asignar</span>
        </span>
      </div>
      <h3 class="titulo">HORARIO</h3>
      <table>
        <thead>
          <tr>
            <th>Horas</th>
            <th v-for="d in DIAS" :key="d.numero">{{ d.nombre }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!filas.length">
            <td :colspan="DIAS.length + 1" class="vacio">Este curso todavía no tiene horarios cargados.</td>
          </tr>
          <tr v-for="f in filas" :key="f.etiqueta">
            <td class="hora">{{ f.etiqueta }}</td>
            <td v-for="d in DIAS" :key="d.numero" class="materia">
              <!-- v-menu en vez de v-tooltip: al pasar el puntero muestra los docentes y no se cierra
                   al moverse hacia los nombres, que son enlaces a la ficha personal. -->
              <v-menu v-if="f.celdas[d.numero]" open-on-hover open-on-click :close-delay="200" location="top">
                <template #activator="{ props }">
                  <span v-bind="props" class="materia-nombre" data-test="materia">{{ f.celdas[d.numero]!.materia }}</span>
                </template>
                <CartelPersonal :lineas="lineasDocentes(f.celdas[d.numero]!)" vacio="Sin docente asignado" data-test="docentes" />
              </v-menu>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.horario { max-width: 860px; }
.encabezado { display: flex; gap: 32px; flex-wrap: wrap; margin-bottom: 8px; }
.titulo { text-align: center; font-size: 1.4rem; letter-spacing: 1px; margin: 8px 0; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { border: 1px solid rgba(var(--v-theme-on-surface), 0.7); padding: 6px 8px; text-align: center; }
th { font-weight: 600; background: rgba(var(--v-theme-on-surface), 0.08); }
td.hora { white-space: nowrap; width: 110px; }
td.materia { height: 44px; }
.materia-nombre { cursor: help; display: inline-block; width: 100%; }
.vacio { padding: 24px; opacity: 0.6; }
.preceptor-nombre { cursor: help; }
</style>
