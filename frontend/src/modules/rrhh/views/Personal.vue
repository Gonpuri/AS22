<script setup lang="ts">
import { ref } from 'vue'
import CrudView from '@/components/CrudView.vue'
import type { Campo } from '@/components/campos'
import { categorias } from '../opciones'
import { formatoPad } from '../ficha'
import CargaExcelPersonal from './CargaExcelPersonal.vue'

const lista = ref<InstanceType<typeof CrudView> | null>(null)
const cargaExcel = ref(false)

const nombreCategoria = (c: string) => categorias.find((x) => x.value === c)?.title ?? c

const campos: Campo[] = [
  { clave: 'apellido', etiqueta: 'Apellido', requerido: true },
  { clave: 'nombre', etiqueta: 'Nombre', requerido: true },
  { clave: 'dni', etiqueta: 'DNI', requerido: true },
  {
    clave: 'categorias',
    etiqueta: 'Categorías',
    soloLectura: true,
    formato: (v: string[]) => v.map(nombreCategoria).join(', '),
  },
  { clave: 'cuil', etiqueta: 'CUIL', soloFormulario: true },
  { clave: 'fecha_nacimiento', etiqueta: 'Fecha de nacimiento', tipo: 'fecha', soloFormulario: true },
  { clave: 'domicilio', etiqueta: 'Domicilio', soloFormulario: true },
  { clave: 'telefono', etiqueta: 'Teléfono' },
  { clave: 'email', etiqueta: 'Email', tipo: 'email' },
  { clave: 'fecha_ingreso', etiqueta: 'Fecha de ingreso', tipo: 'fecha', soloFormulario: true },
  { clave: 'pad', etiqueta: 'PAD', tipo: 'numero', formato: (v) => formatoPad(v) },
  { clave: 'activo', etiqueta: 'Activo', tipo: 'checkbox' },
]
</script>

<template>
  <CrudView ref="lista" titulo="Personal" endpoint="/api/rrhh/personal" :campos="campos">
    <template #acciones>
      <v-btn color="primary" prepend-icon="mdi-file-excel" data-test="carga-excel" @click="cargaExcel = true">
        Carga Excel
      </v-btn>
    </template>
  </CrudView>
  <CargaExcelPersonal v-model="cargaExcel" @importado="lista?.cargar()" />
</template>
