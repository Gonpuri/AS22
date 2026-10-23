<script setup lang="ts">
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'

const campos: Campo[] = [
  { clave: 'username', etiqueta: 'Usuario', requerido: true },
  { clave: 'password', etiqueta: 'Contraseña', tipo: 'password', requerido: true, soloFormulario: true },
  { clave: 'first_name', etiqueta: 'Nombre' },
  { clave: 'last_name', etiqueta: 'Apellido' },
  { clave: 'email', etiqueta: 'Email', tipo: 'email' },
  { clave: 'is_staff', etiqueta: 'Administrador', tipo: 'checkbox', porDefecto: false },
  { clave: 'is_active', etiqueta: 'Activo', tipo: 'checkbox' },
]
</script>

<template>
  <CrudView titulo="Usuarios" endpoint="/api/administracion/usuarios" :campos="campos" />
</template>
