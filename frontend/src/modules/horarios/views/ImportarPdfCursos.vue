<script setup lang="ts">
import { computed, ref } from 'vue'
import { http, mensajeError } from '@/api/http'
import { useOpciones } from '@/api/opciones'
import { auth } from '@/stores/auth'

interface Bloque {
  dia: number
  hora_inicio: string
  hora_fin: string
  materia: number | null
  materia_nombre: string
}
interface Curso {
  anio: number
  division: string
  turno: string
  modalidad: string
  preceptor: string
  division_id: number | null
  bloques: Bloque[]
  advertencias: string[]
}
interface Leido extends Curso {
  pagina: number
  incluir: boolean
  reemplazar: boolean
}

const DIAS = ['', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie']
const TURNOS: Record<string, string> = { manana: 'Mañana', tarde: 'Tarde', vespertino: 'Vespertino' }
const hhmm = (h: string) => h.slice(0, 5)

const materias = useOpciones('/api/academico/materias', (m) => m.nombre)
const archivo = ref<File | File[] | null>(null)
const cursos = ref<Leido[]>([])
const errores = ref<{ pagina: number; mensaje: string }[]>([])
const progreso = ref({ hechas: 0, total: 0 })
const leyendo = ref(false)
const guardando = ref(false)
const error = ref('')
const resultado = ref('')

const pdf = computed(() => (Array.isArray(archivo.value) ? archivo.value[0] : archivo.value) ?? null)
const elegidos = computed(() => cursos.value.filter((c) => c.incluir))
const sinBloques = computed(() => elegidos.value.some((c) => c.bloques.length === 0))
const puedeGuardar = computed(() => elegidos.value.length > 0 && !sinBloques.value && !leyendo.value && !guardando.value)

/** Opciones de un bloque: las materias existentes y, si no se reconoció, crear la leída. */
const opcionesDe = (b: Bloque) =>
  b.materia === null ? [{ value: null, title: `Crear «${b.materia_nombre}»` }, ...materias.value] : materias.value
const etiqueta = (c: Curso) => `${c.anio}° ${c.division}`
const nuevas = (c: Curso) => new Set(c.bloques.filter((b) => b.materia === null).map((b) => b.materia_nombre)).size

function reiniciar() {
  cursos.value = []
  errores.value = []
  error.value = ''
  resultado.value = ''
  progreso.value = { hechas: 0, total: 0 }
}

async function leerPagina(pagina: number) {
  const datos = new FormData()
  datos.append('pagina', String(pagina))
  datos.append('archivo', pdf.value as File)
  const { data } = await http.post<{ paginas: number; curso: Curso }>('/api/horarios/importar/pdf/leer', datos)
  return data
}

async function leer() {
  reiniciar()
  if (!pdf.value) return
  leyendo.value = true
  try {
    const primera = await leerPagina(1)
    progreso.value = { hechas: 1, total: primera.paginas }
    cursos.value.push({ ...primera.curso, pagina: 1, incluir: true, reemplazar: false })
    for (let pagina = 2; pagina <= primera.paginas; pagina++) {
      try {
        const { curso } = await leerPagina(pagina)
        cursos.value.push({ ...curso, pagina, incluir: true, reemplazar: false })
      } catch (e) {
        errores.value.push({ pagina, mensaje: mensajeError(e) })
      }
      progreso.value.hechas = pagina
    }
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
    const { data } = await http.post<{
      creados: number
      existentes: number
      eliminados: number
      divisiones_creadas: number
      materias_creadas: number
    }>('/api/horarios/importar/cursos', {
      cursos: elegidos.value.map((c) => ({
        anio: c.anio,
        division: c.division,
        turno: c.turno,
        modalidad: c.modalidad,
        reemplazar: c.reemplazar,
        bloques: c.bloques,
      })),
    })
    resultado.value =
      `Guardado: ${data.creados} bloques en ${elegidos.value.length} cursos` +
      (data.divisiones_creadas ? `, ${data.divisiones_creadas} divisiones nuevas` : '') +
      (data.materias_creadas ? `, ${data.materias_creadas} materias nuevas` : '') +
      (data.existentes ? `, ${data.existentes} bloques ya existían` : '') +
      (data.eliminados ? `, ${data.eliminados} anteriores reemplazados` : '') +
      '.'
    cursos.value = []
  } catch (e) {
    error.value = mensajeError(e)
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <div>
    <h2 class="text-h5 mb-2">Carga IA: horarios desde PDF escaneado</h2>
    <v-alert v-if="!auth.esAdmin.value" type="info" data-test="solo-admin">
      Solo los administradores pueden cargar horarios.
    </v-alert>
    <template v-else>
      <p class="mb-4 text-medium-emphasis">
        Subí un PDF con un curso por página (fotos o escaneos). Una IA lee el encabezado (curso, división, turno,
        modalidad) y la grilla de cada página; vos revisás todo antes de guardar. Las divisiones y materias que falten se
        crean solas.
      </p>
      <v-file-input
        v-model="archivo"
        label="PDF con los horarios"
        accept="application/pdf,.pdf"
        style="max-width: 480px"
        data-test="archivo"
        @update:model-value="reiniciar"
      />
      <v-btn color="primary" :disabled="!pdf || leyendo" :loading="leyendo" data-test="leer" @click="leer">
        Leer PDF
      </v-btn>
      <span v-if="progreso.total" class="ml-4" data-test="progreso">
        Página {{ progreso.hechas }} de {{ progreso.total }}
      </span>
      <v-progress-linear v-if="leyendo" :model-value="(progreso.hechas / progreso.total) * 100" class="mt-2" />

      <v-alert v-if="error" type="error" class="mt-4" data-test="error">{{ error }}</v-alert>
      <v-alert v-if="resultado" type="success" class="mt-4" data-test="resultado">{{ resultado }}</v-alert>
      <v-alert v-for="e in errores" :key="e.pagina" type="warning" class="mt-4" data-test="error-pagina">
        Página {{ e.pagina }}: {{ e.mensaje }}
      </v-alert>

      <template v-if="cursos.length">
        <v-expansion-panels class="mt-4" multiple>
          <v-expansion-panel v-for="c in cursos" :key="c.pagina" data-test="curso">
            <v-expansion-panel-title>
              <v-checkbox-btn v-model="c.incluir" class="flex-grow-0 mr-2" @click.stop />
              <b>{{ etiqueta(c) }}</b>
              <span class="ml-3">{{ TURNOS[c.turno] }} · {{ c.modalidad || 'sin modalidad' }}</span>
              <v-chip size="small" class="ml-3" :color="c.division_id ? undefined : 'info'">
                {{ c.division_id ? 'curso existente' : 'curso nuevo' }}
              </v-chip>
              <v-chip v-if="nuevas(c)" size="small" class="ml-2" color="warning">{{ nuevas(c) }} materias nuevas</v-chip>
              <v-chip v-if="c.advertencias.length" size="small" class="ml-2" color="warning">avisos</v-chip>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p class="text-medium-emphasis">Preceptor/a: {{ c.preceptor || '—' }} · página {{ c.pagina }} del PDF</p>
              <v-alert v-for="a in c.advertencias" :key="a" type="warning" density="compact" class="my-2">{{ a }}</v-alert>
              <v-table density="compact">
                <thead>
                  <tr><th>Día</th><th>Desde</th><th>Hasta</th><th>Materia</th><th /></tr>
                </thead>
                <tbody>
                  <tr v-for="(b, i) in c.bloques" :key="i" :class="{ nueva: b.materia === null }">
                    <td>{{ DIAS[b.dia] }}</td>
                    <td>{{ hhmm(b.hora_inicio) }}</td>
                    <td>{{ hhmm(b.hora_fin) }}</td>
                    <td style="min-width: 260px">
                      <v-select v-model="b.materia" :items="opcionesDe(b)" density="compact" hide-details />
                    </td>
                    <td>
                      <v-btn icon="mdi-close" size="small" variant="text" title="Quitar" @click="c.bloques.splice(i, 1)" />
                    </td>
                  </tr>
                </tbody>
              </v-table>
              <v-checkbox
                v-if="c.division_id"
                v-model="c.reemplazar"
                label="Reemplazar el horario actual de este curso"
                hide-details
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
        <v-btn color="primary" class="mt-4" :disabled="!puedeGuardar" :loading="guardando" data-test="guardar" @click="guardar">
          Guardar {{ elegidos.length }} cursos
        </v-btn>
      </template>
    </template>
  </div>
</template>

<style scoped>
.nueva {
  background: rgba(var(--v-theme-warning), 0.15);
}
</style>
