<script setup lang="ts">
import { computed, ref } from 'vue'
import { http, mensajeError } from '@/api/http'
import { fechaLarga, fechasSinClases, filasDeClases, type RespuestaConsulta } from '../consulta'

const cuil = ref('')
const desde = ref('')
const hasta = ref('')
const resultado = ref<RespuestaConsulta | null>(null)
const error = ref('')
const cargando = ref(false)

const encabezados = [
  { title: 'Fecha', key: 'fecha', sortable: false },
  { title: 'Horario', key: 'horario', sortable: false },
  { title: 'Curso', key: 'curso', sortable: false },
  { title: 'Materia', key: 'materia', sortable: false },
  { title: 'Situación de revista', key: 'situacion_revista', sortable: false },
]

const filas = computed(() => filasDeClases(resultado.value?.dias ?? []))
const sinClases = computed(() => fechasSinClases(resultado.value?.dias ?? []))
const periodo = computed(() => {
  const r = resultado.value
  if (!r) return ''
  return r.desde === r.hasta ? `el ${fechaLarga(r.desde)}` : `entre el ${fechaLarga(r.desde)} y el ${fechaLarga(r.hasta)}`
})

async function consultar() {
  error.value = ''
  resultado.value = null
  cargando.value = true
  try {
    const params: Record<string, string> = { cuil: cuil.value, desde: desde.value }
    if (hasta.value) params.hasta = hasta.value
    resultado.value = (await http.get<RespuestaConsulta>('/api/consulta_docente/', { params })).data
  } catch (e) {
    error.value = mensajeError(e)
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div>
    <h2 class="text-h5 mb-4">Clases de un docente por fecha</h2>
    <v-form class="formulario" @submit.prevent="consultar">
      <v-text-field v-model="cuil" label="CUIL del docente" placeholder="20-12345678-9" data-test="cuil" />
      <v-text-field v-model="desde" label="Desde" type="date" data-test="desde" />
      <v-text-field v-model="hasta" label="Hasta (opcional)" type="date" hint="Vacío: se consulta solo el día elegido" persistent-hint data-test="hasta" />
      <v-btn type="submit" color="primary" :loading="cargando" :disabled="!cuil || !desde" data-test="consultar">Consultar</v-btn>
    </v-form>

    <v-alert v-if="error" type="error" class="mt-4" data-test="error">{{ error }}</v-alert>

    <template v-if="resultado">
      <v-alert :type="resultado.tiene_clases ? 'info' : 'warning'" class="mt-4" data-test="resumen">
        <b>{{ resultado.docente.apellido }}, {{ resultado.docente.nombre }}</b>
        <template v-if="resultado.tiene_clases"> tiene clases {{ periodo }}.</template>
        <template v-else-if="resultado.cursos_asignados === 0"> no tiene cursos ni materias asignados.</template>
        <template v-else> no tiene clases {{ periodo }}.</template>
      </v-alert>

      <v-data-table
        v-if="filas.length"
        :headers="encabezados"
        :items="filas"
        :items-per-page="-1"
        hide-default-footer
        class="mt-4"
        data-test="tabla"
      />
      <p v-if="filas.length && sinClases.length" class="mt-4 text-medium-emphasis" data-test="sin-clases">
        Sin clases: {{ sinClases.join(', ') }}
      </p>
    </template>
  </div>
</template>

<style scoped>
.formulario { display: grid; gap: 4px; max-width: 360px; }
</style>
