<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '@/stores/auth'
import { mensajeError } from '@/api/http'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const cargando = ref(false)

async function ingresar() {
  error.value = ''
  cargando.value = true
  try {
    await auth.ingresar(username.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = mensajeError(e)
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <v-main class="d-flex align-center justify-center">
    <v-card width="360" class="pa-4">
      <v-card-title>Sistema Escolar</v-card-title>
      <v-form @submit.prevent="ingresar">
        <v-text-field v-model="username" label="Usuario" autofocus />
        <v-text-field v-model="password" label="Contraseña" type="password" />
        <v-alert v-if="error" type="error" class="mb-4" density="compact">{{ error }}</v-alert>
        <v-btn type="submit" color="primary" block :loading="cargando">Ingresar</v-btn>
      </v-form>
    </v-card>
  </v-main>
</template>
