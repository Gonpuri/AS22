<script setup lang="ts">
import { computed, ref } from 'vue'
import { http, mensajeError } from '@/api/http'
import { useOpciones } from '@/api/opciones'
import { auth } from '@/stores/auth'

interface Propuesto {
  dia: number
  hora_inicio: string
  hora_fin: string
  materia: number | null
  texto: string
}

const DIAS = ['', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
const hhmm = (h: string) => h.slice(0, 5)

const divisiones = useOpciones('/api/academico/divisiones', (d) => d.etiqueta)
const materias = useOpciones('/api/academico/materias', (m) => m.nombre)
const divisionId = ref<number | null>(null)
const archivo = ref<File | File[] | null>(null)
const bloques = ref<Propuesto[]>([])
const reemplazar = ref(false)
const cargando = ref(false)
const error = ref('')
const resultado = ref('')

const pdf = computed(() => (Array.isArray(archivo.value) ? archivo.value[0] : archivo.value) ?? null)
const sinMateria = computed(() => bloques.value.filter((b) => b.materia === null).length)
const puedeGuardar = computed(() => bloques.value.length > 0 && sinMateria.value === 0 && !cargando.value)

function reiniciar() {
  bloques.value = []
  error.value = ''
  resultado.value = ''
}

async function leer() {
  reiniciar()
  if (divisionId.value === null || !pdf.value) return
  const datos = new FormData()
  datos.append('division', String(divisionId.value))
  datos.append('archivo', pdf.value)
  cargando.value = true
  try {
    const { data } = await http.post<{ bloques: Propuesto[] }>('/api/horarios/importar/previsualizar', datos)
    bloques.value = data.bloques
  } catch (e) {
    error.value = mensajeError(e)
  } finally {
    cargando.value = false
  }
}

async function guardar() {
  error.value = ''
  cargando.value = true
  try {
    const { data } = await http.post<{ creados: number; existentes: number; eliminados: number }>(
      '/api/horarios/importar',
      {
        division: divisionId.value,
        reemplazar: reemplazar.value,
        bloques: bloques.value.map(({ dia, hora_inicio, hora_fin, materia }) => ({ dia, hora_inicio, hora_fin, materia })),
      },
    )
    resultado.value =
      `Horario guardado: ${data.creados} bloques creados` +
      (data.existentes ? `, ${data.existentes} ya existían` : '') +
      (data.eliminados ? `, ${data.eliminados} anteriores reemplazados` : '') +
      '.'
    bloques.value = []
  } catch (e) {
    error.value = mensajeError(e)
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div>
    <h2 class="text-h5 mb-2">Cargar horario completo desde PDF</h2>
    <v-alert v-if="!auth.esAdmin.value" type="info" data-test="solo-admin">
      Solo los administradores pueden cargar horarios.
    </v-alert>
    <template v-else>
    <p class="mb-4 text-medium-emphasis">
      Elegí el curso y subí el PDF del horario (tabla con los días en columnas y las franjas horarias en la primera
      columna). Antes de guardar vas a poder revisar y corregir lo que se leyó.
    </p>

    <v-select
      v-model="divisionId"
      :items="divisiones"
      label="Curso y división"
      style="max-width: 320px"
      data-test="division"
      @update:model-value="reiniciar"
    />
    <v-file-input
      v-model="archivo"
      label="Horario en PDF"
      accept="application/pdf,.pdf"
      style="max-width: 480px"
      data-test="archivo"
      @update:model-value="reiniciar"
    />
    <v-btn color="primary" :disabled="divisionId === null || !pdf || cargando" :loading="cargando" data-test="leer" @click="leer">
      Leer PDF
    </v-btn>

    <v-alert v-if="error" type="error" class="mt-4" data-test="error">{{ error }}</v-alert>
    <v-alert v-if="resultado" type="success" class="mt-4" data-test="resultado">{{ resultado }}</v-alert>

    <template v-if="bloques.length">
      <v-alert v-if="sinMateria" type="warning" class="mt-4" data-test="faltan">
        {{ sinMateria }} {{ sinMateria === 1 ? 'celda no se pudo' : 'celdas no se pudieron' }} relacionar con una materia:
        elegí la materia en cada fila marcada o quitá la fila.
      </v-alert>
      <v-table class="mt-4" density="compact" data-test="propuesta">
        <thead>
          <tr><th>Día</th><th>Desde</th><th>Hasta</th><th>Decía el PDF</th><th>Materia</th><th /></tr>
        </thead>
        <tbody>
          <tr v-for="(b, i) in bloques" :key="i" :class="{ 'sin-materia': b.materia === null }">
            <td>{{ DIAS[b.dia] }}</td>
            <td>{{ hhmm(b.hora_inicio) }}</td>
            <td>{{ hhmm(b.hora_fin) }}</td>
            <td>{{ b.texto }}</td>
            <td style="min-width: 240px">
              <v-select v-model="b.materia" :items="materias" density="compact" hide-details data-test="materia" />
            </td>
            <td>
              <v-btn icon="mdi-close" size="small" variant="text" title="Quitar" @click="bloques.splice(i, 1)" />
            </td>
          </tr>
        </tbody>
      </v-table>
      <v-checkbox
        v-model="reemplazar"
        label="Reemplazar el horario actual de este curso (se borran sus bloques actuales)"
        hide-details
        data-test="reemplazar"
      />
      <v-btn color="primary" class="mt-2" :disabled="!puedeGuardar" :loading="cargando" data-test="guardar" @click="guardar">
        Guardar horario ({{ bloques.length }} bloques)
      </v-btn>
    </template>
    </template>
  </div>
</template>

<style scoped>
.sin-materia {
  background: rgba(var(--v-theme-warning), 0.15);
}
</style>
