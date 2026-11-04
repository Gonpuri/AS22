<script setup lang="ts">
import { computed, ref } from 'vue'
import { http, mensajeError } from '@/api/http'

interface Fila {
  fila: number
  dni: string
  datos: Record<string, unknown>
  accion: 'crear' | 'actualizar' | 'error'
  errores: string[]
  cambios: string[]
}

const abierto = defineModel<boolean>({ default: false })
const emit = defineEmits<{ importado: [] }>()

const ACCIONES = { crear: ['Nueva', 'success'], actualizar: ['Existente', 'info'], error: ['Con error', 'error'] } as const
const CAMPOS: Record<string, string> = {
  apellido: 'apellido', nombre: 'nombre', cuil: 'CUIL', fecha_nacimiento: 'fecha de nacimiento',
  domicilio: 'domicilio', telefono: 'teléfono', email: 'email', fecha_ingreso: 'fecha de ingreso', pad: 'PAD',
}

const archivo = ref<File | File[] | null>(null)
const filas = ref<Fila[]>([])
const leyendo = ref(false)
const guardando = ref(false)
const error = ref('')
const resultado = ref('')

const planilla = computed(() => (Array.isArray(archivo.value) ? archivo.value[0] : archivo.value) ?? null)
const validas = computed(() => filas.value.filter((f) => f.accion !== 'error'))
const conError = computed(() => filas.value.length - validas.value.length)
const cuenta = (accion: Fila['accion']) => filas.value.filter((f) => f.accion === accion).length
const nombre = (f: Fila) => [f.datos.apellido, f.datos.nombre].filter(Boolean).join(', ')
const detalle = (f: Fila) =>
  f.accion === 'error'
    ? f.errores.join(' · ')
    : f.accion === 'crear'
      ? ''
      : f.cambios.length
        ? 'Completa: ' + f.cambios.map((c) => CAMPOS[c] ?? c).join(', ')
        : 'Sin cambios'

function reiniciar() {
  filas.value = []
  error.value = ''
  resultado.value = ''
}

function cerrar() {
  abierto.value = false
  archivo.value = null
  reiniciar()
}

async function leer() {
  reiniciar()
  if (!planilla.value) return
  const datos = new FormData()
  datos.append('archivo', planilla.value)
  leyendo.value = true
  try {
    const { data } = await http.post<{ filas: Fila[] }>('/api/rrhh/personal/importar-excel/previsualizar/', datos)
    filas.value = data.filas
  } catch (e) {
    error.value = mensajeError(e)
  } finally {
    leyendo.value = false
  }
}

async function guardar() {
  error.value = ''
  guardando.value = true
  try {
    const { data } = await http.post<{ creados: number; actualizados: number; sin_cambios: number }>(
      '/api/rrhh/personal/importar-excel/',
      { filas: validas.value.map((f) => ({ ...f.datos, dni: f.dni })) },
    )
    resultado.value =
      `Listo: ${data.creados} personas nuevas, ${data.actualizados} actualizadas` +
      (data.sin_cambios ? `, ${data.sin_cambios} sin cambios` : '') +
      '.'
    filas.value = []
    emit('importado')
  } catch (e) {
    error.value = mensajeError(e)
  } finally {
    guardando.value = false
  }
}

defineExpose({ leer, guardar })
</script>

<template>
  <v-dialog v-model="abierto" max-width="900" scrollable>
    <v-card title="Carga de personal desde Excel">
      <v-card-text>
        <p class="mb-4 text-medium-emphasis">
          Subí una planilla (.xlsx) con una fila de encabezados y una persona por fila. La clave es el
          <b>DNI</b>: si ya existe se completan sus datos vacíos o distintos, y si no, se crea. Columnas
          reconocidas: DNI, Apellido, Nombre (o «Apellido y nombre»), CUIL, Fecha de nacimiento, Domicilio,
          Teléfono, Email, Fecha de ingreso y PAD. Las celdas vacías nunca borran datos ya cargados.
        </p>
        <v-file-input
          v-model="archivo"
          label="Planilla de Excel"
          accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          data-test="archivo"
          @update:model-value="reiniciar"
        />
        <v-btn color="primary" :disabled="!planilla || leyendo" :loading="leyendo" data-test="leer" @click="leer">
          Leer planilla
        </v-btn>

        <v-alert v-if="error" type="error" class="mt-4" data-test="error">{{ error }}</v-alert>
        <v-alert v-if="resultado" type="success" class="mt-4" data-test="resultado">{{ resultado }}</v-alert>

        <template v-if="filas.length">
          <p class="mt-4" data-test="resumen">
            {{ cuenta('crear') }} nuevas · {{ cuenta('actualizar') }} existentes · {{ conError }} con error
            <span v-if="conError" class="text-medium-emphasis">(las filas con error no se guardan)</span>
          </p>
          <v-table density="compact" class="mt-2" data-test="propuesta">
            <thead>
              <tr><th>Fila</th><th>DNI</th><th>Apellido y nombre</th><th>Estado</th><th>Detalle</th></tr>
            </thead>
            <tbody>
              <tr v-for="f in filas" :key="f.fila">
                <td>{{ f.fila }}</td>
                <td>{{ f.dni }}</td>
                <td>{{ nombre(f) }}</td>
                <td><v-chip size="small" :color="ACCIONES[f.accion][1]">{{ ACCIONES[f.accion][0] }}</v-chip></td>
                <td>{{ detalle(f) }}</td>
              </tr>
            </tbody>
          </v-table>
        </template>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn data-test="cerrar" @click="cerrar">{{ resultado ? 'Cerrar' : 'Cancelar' }}</v-btn>
        <v-btn
          v-if="filas.length"
          color="primary"
          :disabled="!validas.length || guardando"
          :loading="guardando"
          data-test="guardar"
          @click="guardar"
        >
          Guardar {{ validas.length }} personas
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
