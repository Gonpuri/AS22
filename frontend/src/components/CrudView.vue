<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { crud, type Registro } from '@/api/crud'
import { mensajeError } from '@/api/http'
import { auth } from '@/stores/auth'
import type { Campo } from './campos'

const props = withDefaults(defineProps<{
  titulo: string
  endpoint: string
  campos: Campo[]
  /** DRF exige barra final en las rutas (por defecto); FastAPI no. */
  barraFinal?: boolean
}>(), { barraFinal: true }) // Vue pone en false las props Boolean ausentes: el default evita perder la barra

/** Se emite cada vez que se carga la lista: permite a la pantalla refrescar opciones que dependen de ella. */
const emit = defineEmits<{ cargado: [filas: Registro[]] }>()

const api = crud(props.endpoint, props.barraFinal)
const filas = ref<Registro[]>([])
const error = ref('')
const dialogo = ref(false)
const editando = ref<Registro | null>(null)
const formulario = ref<Record<string, any>>({})
const eliminando = ref<Registro | null>(null)

const puedeEditar = computed(() => auth.esAdmin.value)
const camposEditables = computed(() => props.campos.filter((c) => !c.soloLectura))
const columnas = computed(() => [
  ...props.campos.filter((c) => !c.soloFormulario).map((c) => ({ title: c.etiqueta, key: c.clave })),
  ...(puedeEditar.value ? [{ title: 'Acciones', key: 'acciones', sortable: false }] : []),
])

function texto(campo: Campo, fila: Registro): string {
  const valor = fila[campo.clave]
  if (campo.formato) return campo.formato(valor, fila)
  const titulo = (v: unknown) => campo.opciones?.find((o) => o.value === v)?.title ?? String(v ?? '')
  if (campo.tipo === 'checkbox') return valor ? 'Sí' : 'No'
  if (campo.tipo === 'hora') return String(valor ?? '').slice(0, 5)
  if (campo.tipo === 'multiple') return ((valor ?? []) as unknown[]).map(titulo).join(', ')
  if (campo.tipo === 'select') return titulo(valor)
  return String(valor ?? '')
}

async function cargar() {
  try {
    filas.value = await api.listar()
    emit('cargado', filas.value)
  } catch (e) {
    error.value = mensajeError(e)
  }
}

function valorInicial(c: Campo, fila: Registro | null) {
  if (fila) return c.tipo === 'password' ? '' : fila[c.clave]
  if (c.tipo === 'checkbox') return true
  return c.tipo === 'multiple' ? [] : null
}

function abrir(fila: Registro | null) {
  editando.value = fila
  error.value = ''
  formulario.value = Object.fromEntries(camposEditables.value.map((c) => [c.clave, valorInicial(c, fila)]))
  dialogo.value = true
}

async function guardar() {
  error.value = ''
  // Una contraseña vacía al editar significa "no cambiarla".
  const datos = Object.fromEntries(
    Object.entries(formulario.value).filter(
      ([k, v]) => !(props.campos.find((c) => c.clave === k)?.tipo === 'password' && !v),
    ),
  )
  try {
    if (editando.value) await api.actualizar(editando.value.id, datos)
    else await api.crear(datos)
    dialogo.value = false
    await cargar()
  } catch (e) {
    error.value = mensajeError(e)
  }
}

async function eliminar() {
  if (!eliminando.value) return
  try {
    await api.eliminar(eliminando.value.id)
    error.value = ''
    await cargar()
  } catch (e) {
    error.value = mensajeError(e)
  } finally {
    eliminando.value = null
  }
}

const tipoInput = (t?: string) =>
  ({ numero: 'number', email: 'email', password: 'password', fecha: 'date', hora: 'time' })[t ?? ''] ?? 'text'

onMounted(cargar)
defineExpose({ cargar })
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h2 class="text-h5">{{ titulo }}</h2>
      <v-spacer />
      <v-btn v-if="puedeEditar" color="primary" prepend-icon="mdi-plus" data-test="nuevo" @click="abrir(null)">Nuevo</v-btn>
    </div>
    <v-alert v-if="error && !dialogo" type="error" class="mb-4" closable @click:close="error = ''">{{ error }}</v-alert>

    <v-data-table :headers="columnas" :items="filas" item-value="id" no-data-text="Sin registros">
      <template v-for="c in campos" :key="c.clave" #[`item.${c.clave}`]="{ item }">
        {{ texto(c, item) }}
      </template>
      <template #[`item.acciones`]="{ item }">
        <v-btn icon="mdi-pencil" variant="text" size="small" title="Editar" data-test="editar" @click="abrir(item)" />
        <v-btn icon="mdi-delete" variant="text" size="small" title="Eliminar" data-test="eliminar" @click="eliminando = item" />
      </template>
    </v-data-table>

    <v-dialog v-model="dialogo" max-width="560">
      <v-card :title="editando ? 'Editar' : 'Nuevo'">
        <v-card-text>
          <v-form id="form-crud" @submit.prevent="guardar">
            <template v-for="c in camposEditables" :key="c.clave">
              <v-checkbox v-if="c.tipo === 'checkbox'" v-model="formulario[c.clave]" :label="c.etiqueta" />
              <v-select
                v-else-if="c.tipo === 'select' || c.tipo === 'multiple'"
                v-model="formulario[c.clave]"
                :items="c.opciones ?? []"
                :label="c.etiqueta"
                :multiple="c.tipo === 'multiple'"
                :chips="c.tipo === 'multiple'"
                :clearable="!c.requerido && c.tipo === 'select'"
              />
              <v-text-field
                v-else
                v-model="formulario[c.clave]"
                :label="c.etiqueta + (c.requerido ? ' *' : '')"
                :type="tipoInput(c.tipo)"
                :placeholder="c.tipo === 'password' && editando ? 'Dejar vacío para no cambiarla' : undefined"
              />
            </template>
          </v-form>
          <v-alert v-if="error" type="error" density="compact">{{ error }}</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialogo = false">Cancelar</v-btn>
          <v-btn color="primary" type="submit" form="form-crud" data-test="guardar">Guardar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog :model-value="!!eliminando" max-width="400" @update:model-value="eliminando = null">
      <v-card title="Confirmar eliminación" text="Esta acción no se puede deshacer.">
        <v-card-actions>
          <v-spacer />
          <v-btn @click="eliminando = null">Cancelar</v-btn>
          <v-btn color="error" data-test="confirmar-eliminar" @click="eliminar">Eliminar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
