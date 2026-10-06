# StreakUp

Aplicación para crear hábitos, registrar progreso y mantener rachas. Incluye
interfaz web y móvil, una API y soporte de almacenamiento offline.

## Estructura

```text
StreakUp/
├── android/       Aplicación nativa Android (Capacitor)
├── backend/       API Flask, modelos, migraciones y pruebas
├── data/db/       Esquema SQLite y datos semilla versionados
├── docs/          Guías operativas y documentación
├── frontend/      Interfaz Next.js y pruebas
├── Makefile       Comandos de desarrollo y validación
└── README.md
```

`data/app.db`, los archivos de entorno, las dependencias y los builds se crean o
configuran localmente; no se versionan.

## Requisitos

- Python 3.12 (consulta `.python-version`)
- Node.js y npm
- `make` y `sqlite3`

## Probar rápidamente en modo offline

```bash
cd frontend
npm ci
NEXT_PUBLIC_OFFLINE_MODE=true npm run dev
```

Abre <http://localhost:3000>. En este modo no es necesario iniciar la API.

## Despliegue web conectado

El frontend se sirve en Vercel y la API Flask en Render. PostgreSQL puede
alojarse en Neon. Los tres servicios se configuran por separado; el manifiesto
[`../render.yaml`](../render.yaml) prepara la API de Render.

### API y PostgreSQL

1. Crea una base PostgreSQL en Neon y copia su URL de conexión, conservándola
   como secreto.
2. En Render, crea un **Blueprint** desde el repositorio
   `jacobocastillo/mis-proyectos` y acepta el servicio `streakup-api` de
   `render.yaml`.
3. En las variables del servicio, configura `DATABASE_URL` con la URL de Neon
   y `CORS_ALLOWED_ORIGINS` con el dominio del frontend en Vercel. Render genera
   `SECRET_KEY` y `JWT_SECRET_KEY`. El arranque aplica las migraciones y carga
   el catálogo.
4. Espera a que el API responda en `/readyz` antes de conectar el frontend.

### Frontend en Vercel

1. Importa `jacobocastillo/mis-proyectos` en Vercel y configura **Root
   Directory** como `StreakUp/frontend`.
2. Deja el comando de build como `npm run build` y el output de Next.js por
   defecto; no actives el export móvil de Capacitor.
3. Configura estas variables para Production, Preview y Development:
   - `NEXT_PUBLIC_OFFLINE_MODE=false`
   - `NEXT_PUBLIC_API_URL=https://<dominio-del-api-en-render>`
4. Despliega el frontend y añade su dominio en
   `CORS_ALLOWED_ORIGINS` en Render.

No pongas `localhost` como `NEXT_PUBLIC_API_URL` en Vercel: ese nombre se
referiría al propio servidor de Vercel. No publiques credenciales en el
frontend; cualquier variable `NEXT_PUBLIC_*` es visible en el navegador.

Neon Free ofrece actualmente 1 GB de almacenamiento por proyecto, no requiere
tarjeta y suspende el cómputo tras cinco minutos sin actividad. Render Free
puede suspender la API por inactividad, y el primer acceso posterior puede
tardar en arrancar. Consulta los límites vigentes de cada proveedor antes de
usar estos planes con datos importantes.

## Ejecutar la app conectada

Instala las dependencias una vez:

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
cd frontend && npm ci
cd ..
```

En la primera ejecucion, crea la base local y el catalogo:

```bash
make db-init
```

> `make db-init` reinicia `data/app.db`. No lo ejecutes si ya tienes datos que
> quieras conservar.

Abre dos terminales desde la raiz de `StreakUp`.

Terminal 1, inicia la API:

```bash
FLASK_ENV=development FLASK_DEBUG=true make run_backend
```

Terminal 2, inicia la interfaz conectada al backend local:

```bash
cd frontend
NEXT_DEV_API_PROXY_URL=http://localhost:5000 \
NEXT_PUBLIC_OFFLINE_MODE=false \
npm run dev
```

Abre <http://localhost:3000>. El proxy envia las peticiones `/api` a Flask en
el puerto `5000`.

## Comandos útiles

Ejecuta desde la raiz del proyecto:

| Comando | Proposito |
|---|---|
| `make run_backend` | Iniciar la API |
| `make run_frontend` | Iniciar la interfaz |
| `make run_local` | Iniciar la interfaz en modo offline |
| `make test_backend` | Ejecutar las pruebas de Flask |
| `make test_frontend_unit` | Ejecutar las pruebas unitarias web |
| `make build_frontend` | Crear el build web |
| `make update-apk-auto` | Sincronizar Capacitor y crear el APK debug |

Android Studio y el SDK de Android solo son necesarios para compilar o ejecutar
la aplicación nativa. El proyecto móvil se configura desde `frontend/` con
Capacitor; `android/` contiene el wrapper nativo.

## Configuración

Usa los archivos de ejemplo como referencia y crea archivos `.env` locales
cuando hagan falta:

- `backend/.env.example`
- `frontend/.env.example`

No subas claves, tokens, bases de datos ni archivos `.env` al repositorio.
`OPENAI_API_KEY` es opcional y solo se requiere para la validación de hábitos
con fotos.

Para despliegue, privacidad y operacion, consulta [`docs/`](./docs/).
