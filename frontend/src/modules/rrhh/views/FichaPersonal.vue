<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http, mensajeError } from '@/api/http'
import { datosPersonales, filaDesignacion, type DesignacionPersona, type Persona } from '../ficha'

const route = useRoute()
const router = useRouter()
const persona = ref<Persona | null>(null)
const designaciones = ref<DesignacionPersona[]>([])
const error = ref('')

const datos = computed(() => (persona.value ? datosPersonales(persona.value) : []))
const filas = computed(() => designaciones.value.map(filaDesignacion))
const encabezados = [
  { title: 'Categoría', key: 'categoria', sortable: false },
  { title: 'Turno', key: 'turno', sortable: false },
  { title: 'Situación de revista', key: 'situacion', sortable: false },
  { title: 'Cargo / función', key: 'cargo', sortable: false },
]

onMounted(async () => {
  const id = route.params.id
  try {
    persona.value = (await http.get<Persona>(`/api/rrhh/personal/${id}/`)).data
    designaciones.value = (await http.get<DesignacionPersona[]>('/api/rrhh/designaciones/', { params: { personal: id } })).data
  } catch (e) {
    error.value = mensajeError(e)
  }
})
</script>

<template>
  <div>
    <v-btn variant="text" prepend-icon="mdi-arrow-left" class="mb-2" data-test="volver" @click="router.back()">Volver</v-btn>
    <v-alert v-if="error" type="error" data-test="error">{{ error }}</v-alert>

    <template v-if="persona">
      <h2 class="text-h5 mb-4" data-test="titulo">{{ persona.apellido }}, {{ persona.nombre }}</h2>

      <v-card class="mb-6" title="Datos personales">
        <v-list lines="one" density="compact" data-test="datos">
          <v-list-item v-for="d in datos" :key="d.etiqueta">
            <template #title>
              <span class="text-medium-emphasis etiqueta">{{ d.etiqueta }}</span>
              <span>{{ d.valor }}</span>
            </template>
          </v-list-item>
        </v-list>
      </v-card>

      <h3 class="text-h6 mb-2">Designaciones</h3>
      <v-data-table
        :headers="encabezados"
        :items="filas"
        :items-per-page="-1"
        hide-default-footer
        no-data-text="Sin designaciones"
        data-test="designaciones"
      />
    </template>
  </div>
</template>

<style scoped>
.etiqueta { display: inline-block; min-width: 170px; }
</style>
