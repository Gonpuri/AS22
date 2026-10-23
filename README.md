# Sistema Escolar

Aplicación web modular para una escuela secundaria de la Provincia de Buenos Aires.

| Capa | Tecnología |
|---|---|
| API | Django REST Framework (estructura académica, administración, RR. HH.) + FastAPI (horarios), servidos por una sola app ASGI |
| Frontend | Vue 3 + TypeScript + Vuetify (Material Design para Vue) |
| Base de datos | PostgreSQL en Render (SQLite local si no hay `DATABASE_URL`) |
| Despliegue | Base y API en Render (`render.yaml`), frontend en Vercel (`frontend/vercel.json`) |

## Módulos

| Etapa | Módulo | Contenido |
|---|---|---|
| 1 | `academico` | Orientaciones, años, divisiones y materias (asociadas a años y orientaciones) |
| 1 | `core` | Administración del sistema: login por token, usuarios (alta, edición, baja, activar/desactivar, rol administrador) |
| 2 | `horarios` | Bloques horarios (división + materia + día + hora de inicio/fin) y vista de grilla por curso, con el docente de cada materia al pasar el puntero |
| 3 | `rrhh` | Personal y sus designaciones (categoría + turno): preceptores, equipo directivo, profesores, EMATPs y otros. Los docentes tienen cursos y materias asignados |
| 4 | `consulta_docente` | Consulta por CUIL y fechas (un día o un intervalo): indica si el docente tiene clases y en qué cursos, materias y horarios |

### Reglas de negocio
- Una **persona** puede tener varias **designaciones** (categoría + turno: mañana, tarde o vespertino), p. ej. preceptor a la mañana y profesor a la tarde. Cada designación tiene su **situación de revista** (titular, titular interino, suplente o provisional). No se repite la misma categoría en el mismo turno.
- Una designación de **profesor o EMATP** puede tener varias **asignaciones** (división + materia): distintos cursos y distintas materias. La materia debe corresponder a la división.
- Una asignación de un **suplente** debe indicar a quién reemplaza (`suplente_de`): otra asignación del **mismo curso y materia** cuyo docente sea titular, titular interino o provisional (no otro suplente ni él mismo). No se puede borrar a quien tiene suplentes.
- Un **preceptor** se asigna a uno o más cursos (`preceptores`); un curso puede tener varios (por turno, o titular y suplente). Un preceptor suplente indica a quién reemplaza con las mismas reglas que un docente suplente. En la planilla del horario por curso figura como **Preceptor/a** en el encabezado, con situación de revista, suplente de quién y enlace a su ficha.
- En el **horario por curso**, al pasar el puntero (o hacer clic) sobre una materia se ven los docentes con su situación de revista y, para el suplente, a quién reemplaza. Cada nombre es un enlace a la **ficha personal** (`/rrhh/personal/:id`) con sus datos y designaciones.
- Una **división** pertenece a un año y, opcionalmente, a una orientación.
- Las **materias de una división** son las asociadas a su año y, si la materia está asociada a orientaciones, solo si incluye la de la división. Una materia sin orientaciones vale para todas las del año.
- Un **bloque horario** exige: materia de la división, fin posterior al inicio y sin superposición con otro bloque de la misma división el mismo día (lunes a viernes).
- No se puede eliminar un año, orientación, división o materia con registros que dependan de ellos (HTTP 409).
- La **consulta de docentes** cruza las asignaciones del docente (curso + materia) con los bloques horarios de ese curso, según el día de la semana de cada fecha. No tiene en cuenta feriados, asuetos ni licencias. Si titular y suplente están asignados a la misma materia de un curso, ambos figuran con esos bloques. Intervalo máximo: 366 días.
- Los **horarios de 1.º 2.ª a 1.º 6.ª** (2026) se cargan con `python manage.py cargar_horarios_iniciales` (idempotente; reutiliza materias y divisiones existentes). En Render se activa con la variable `CARGAR_HORARIOS_INICIALES=1` (ver `DESPLIEGUE.txt`).
- La barra superior tiene una palanca de **modo claro / oscuro**; la elección se recuerda en cada navegador.
- Las secciones **Estructura académica** y **Administración** (menú y pantallas) son solo para administradores (`is_staff` o superusuario); el resto de los usuarios no las ven y, si escriben la dirección, vuelven al inicio. En la API, la lectura sigue abierta a cualquier usuario autenticado (Horarios y Consulta necesitan cursos y materias) y todas las modificaciones exigen ser administrador.
- Cualquier usuario autenticado consulta; solo los administradores (`is_staff`) modifican.

### Agregar un módulo nuevo (p. ej. Alumnos)
1. Backend: crear `backend/apps/alumnos/` (modelos, migraciones), con `urls.py` (DRF) y/o `api.py` (FastAPI, variable `router`), y agregar `"alumnos"` a `MODULOS` en `config/settings.py`. Las rutas se publican solas en `/api/alumnos/`.
2. Frontend: crear `frontend/src/modules/alumnos/index.ts` exportando un `ModuloFrontend` (ver `modules/types.ts`). El menú y el router lo descubren solos.

## Desarrollo local

### Backend
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser     # el primer administrador
uvicorn config.asgi:app --reload     # http://localhost:8000  (docs de FastAPI en /api/docs)
pytest                               # pruebas
```
Variables (ver `backend/.env.example`): `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DJANGO_DEBUG`.

### Frontend
```powershell
cd frontend
npm install
npm run dev      # http://localhost:5173
npm test         # pruebas (Vitest)
npm run build    # verifica tipos y genera dist/
```
Variable: `VITE_API_URL` (ver `frontend/.env.example`).

## Despliegue
Paso a paso completo en [DESPLIEGUE.txt](DESPLIEGUE.txt): base PostgreSQL y API en Render (`render.yaml`) y frontend en Vercel (directorio `frontend`).
