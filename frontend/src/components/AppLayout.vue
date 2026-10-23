<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '@/stores/auth'
import { modulos } from '@/modules'
import { useModoOscuro } from '@/stores/tema'

const router = useRouter()
const { oscuro, elegir } = useModoOscuro()
const visibles = computed(() => modulos.filter((m) => !m.soloAdmin || auth.esAdmin.value))

function salir() {
  auth.salir()
  router.push('/login')
}
</script>

<template>
  <v-navigation-drawer permanent>
    <v-list nav>
      <template v-for="m in visibles" :key="m.nombre">
        <v-list-subheader>{{ m.etiqueta }}</v-list-subheader>
        <v-list-item
          v-for="r in m.rutas.filter((x) => !x.oculta)"
          :key="r.path"
          :to="`/${m.nombre}/${r.path}`"
          :prepend-icon="m.icono"
          :title="r.etiqueta"
        />
      </template>
    </v-list>
  </v-navigation-drawer>
  <v-app-bar flat border>
    <v-app-bar-title>Sistema Escolar</v-app-bar-title>
    <v-switch
      :model-value="oscuro"
      hide-details
      density="compact"
      inset
      class="flex-grow-0 mr-2 palanca-tema"
      :title="oscuro ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
      aria-label="Modo oscuro"
      data-test="tema"
      @update:model-value="elegir"
    >
      <template #prepend><v-icon icon="mdi-white-balance-sunny" /></template>
      <template #append><v-icon icon="mdi-weather-night" /></template>
    </v-switch>
    <span class="mr-2">{{ auth.estado.usuario?.username }}</span>
    <v-btn icon="mdi-logout" title="Salir" @click="salir" />
  </v-app-bar>
  <v-main>
    <v-container fluid><router-view /></v-container>
  </v-main>
</template>
