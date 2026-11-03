# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Sistema escolar para una secundaria bonaerense. Todo el texto de la app, los mensajes de error y los commits están en español rioplatense; mantené ese idioma. Las reglas de negocio están en [README.md](README.md) (sección "Reglas de negocio") y el despliegue en [DESPLIEGUE.txt](DESPLIEGUE.txt).

## Comandos

Backend (desde `backend/`; `requirements.txt` está en la **raíz** del repo, no en `backend/`):
```powershell
pip install -r ../requirements.txt
python manage.py migrate
uvicorn config.asgi:app --reload          # http://localhost:8000, docs en /api/docs
pytest                                    # toda la suite (lenta: ~6 min)
pytest tests/test_horarios.py::test_crear_y_listar   # una prueba
```
Frontend (desde `frontend/`):
```powershell
npm run dev          # http://localhost:5173
npm test             # Vitest (jsdom, ~4 min)
npx vitest run tests/GrillaView.test.ts   # un archivo
npm run build        # vue-tsc --noEmit + vite build; es el chequeo de tipos
```
No hay linter configurado. Sin `DATABASE_URL` se usa SQLite local (`backend/db.sqlite3`).

## Arquitectura

**Una sola app ASGI, dos frameworks.** `backend/config/asgi.py` crea una app FastAPI y le monta Django (DRF) en `/`. Cada módulo de `settings.MODULOS` se publica en `/api/<modulo>/` por uno o ambos caminos: `urls.py` (DRF) o `api.py` (variable `router` de FastAPI), descubiertos automáticamente. `horarios` es FastAPI (Pydantic en `schemas.py`); `academico`, `rrhh`, `core` y `consulta_docente` son DRF. Los endpoints FastAPI son síncronos y usan el ORM de Django; la autenticación (token de DRF) y el permiso de administrador se reutilizan con `apps/core/fastapi_auth.py` (`usuario_actual`, `administrador`). El CORS se configura **dos veces** (`corsheaders` para Django y `CORSMiddleware` para FastAPI, ambos desde `config/cors.py`). Un error 500 de FastAPI sale sin cabeceras CORS y el navegador lo muestra como "No se pudo conectar con el servidor": ante ese mensaje, mirá primero los logs del servidor.

**Módulos auto-descubiertos en ambos lados.** Backend: agregar el nombre a `MODULOS` en `config/settings.py`. Frontend: cada `frontend/src/modules/<nombre>/index.ts` exporta un `ModuloFrontend` (`modules/types.ts`) y `modules/index.ts` los encuentra con `import.meta.glob`; menú y router salen de ahí. `soloAdmin` oculta el módulo y redirige; la API igual deja leer a cualquier usuario autenticado y exige `is_staff` para escribir.

**Núcleo de horarios** (`backend/apps/horarios/`):
- `services.py`: `validar_bloque` (materia de la división, fin > inicio, sin superposición) es la única validación de bloques; la usan el CRUD, el comando de carga inicial y las importaciones. `Division.materias()` (en `academico/models.py`) define qué materias valen para una división: las del año y, si tienen orientaciones, solo si incluyen la de la división; una materia sin orientaciones vale para todas del año.
- Importación desde PDF: `importar_pdf.py` (PDF con texto, vía pdfplumber; el menú del frontend ya no la expone pero los endpoints `/importar/previsualizar` e `/importar` siguen) y `importar_ia.py` (**"Carga IA"**: PDF escaneado, una página por curso, leída con la API de Anthropic con salida estructurada JSON). Flujo en dos pasos: `POST /importar/pdf/leer` procesa **una página por llamada** (la pantalla las pide en bucle, para no pasar el timeout de Render) y no guarda nada; `POST /importar/cursos` guarda todo o nada (`services.importar_cursos`): crea año, orientación, división y materias faltantes y habilita cada materia en su división (`vincular_materia`). Las materias se resuelven con `Buscador` en modo `estricto` (sin prefijos: "Matemática" ≠ "Matemática Ciclo Superior"); el prompt le pide a la IA el nombre completo de la tabla MATERIAS de cada página. Requiere `ANTHROPIC_API_KEY` (y opcionalmente `ANTHROPIC_MODEL`, por defecto `claude-opus-5-5`); sin ella devuelve 502 con mensaje claro.
- `cargar_horarios_iniciales` carga `datos/horarios_1er_anio_2026.json`; es idempotente y en Render se activa con `CARGAR_HORARIOS_INICIALES=1`.

**Frontend** (Vue 3 + Vuetify 4 + TypeScript): `api/http.ts` es el cliente axios (token en `localStorage`; reintenta GET y login porque el plan gratuito de Render duerme la API) y `mensajeError` traduce errores de DRF/FastAPI. `components/CrudView.vue` + `campos.ts` arman pantallas CRUD genéricas a partir de una lista de campos (ver `horarios/views/Bloques.vue`). Las pruebas de vistas montan el componente con Vuetify real, mockean `http` con `vi.spyOn` y manipulan `wrapper.vm` directamente.

## Despliegue y trampas

- `render.yaml` (Blueprint): sin `rootDir`; build y arranque hacen `cd backend`. Arranca con **uvicorn**, no gunicorn (`gunicorn` no está instalado). Variables a cargar a mano: `ADMIN_PASSWORD`, `CORS_ALLOWED_ORIGINS` (URL de Vercel, sin barra final) y `ANTHROPIC_API_KEY`.
- `DATABASE_URL` se lee en `settings._base_de_datos()`, que tolera comillas y espacios y, si es inválida, falla explicando qué revisar sin mostrar la clave. La base PostgreSQL gratuita de Render vence: hacer respaldos (`pg_dump`) antes de cargas grandes.
- El frontend (Vercel) toma `VITE_API_URL` en el **build**: si cambia la URL de la API hay que redesplegar el frontend, no alcanza con editar la variable. La URL de Render cambia si se recrea el servicio.
- Python 3.14 en Render (versión por defecto); las dependencias deben tener ruedas para esa versión.
- Windows: Git avisa de conversión LF→CRLF en cada commit; es esperado.
