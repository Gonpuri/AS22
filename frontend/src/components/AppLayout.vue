<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '@/stores/auth'
import { modulos } from '@/modules'

const router = useRouter()
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
          v-for="r in m.rutas"
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
    <span class="mr-2">{{ auth.estado.usuario?.username }}</span>
    <v-btn icon="mdi-logout" title="Salir" @click="salir" />
  </v-app-bar>
  <v-main>
    <v-container fluid><router-view /></v-container>
  </v-main>
</template>
