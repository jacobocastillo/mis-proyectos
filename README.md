# Mis proyectos

Repositorio para organizar mis proyectos personales. Cada proyecto vive en su
propia carpeta para mantener su código y documentación separados.

## Proyectos

- [StreakUp](./StreakUp/README.md): aplicación de hábitos con frontend web y API.

### ¿Por qué StreakUp tiene varias carpetas?

No son proyectos duplicados: cada carpeta principal es una pieza necesaria de
la aplicación:

- `frontend/`: aplicación web.
- `backend/`: API y lógica de negocio.
- `android/`: integración nativa para compilar la app móvil.
- `data/db/`: esquemas SQL y datos de ejemplo; no contiene la base de datos
  personal.
- `docs/`: guías operativas.

Las carpetas internas de `frontend/` y `backend/` siguen la organización normal
de Next.js y Flask. Los entornos, las bases de datos locales, credenciales y
archivos de compilación no se suben a GitHub.

## Añadir un proyecto

1. Crea una carpeta en la raíz, por ejemplo `MiProyecto/`.
2. Añade el código y un `README.md` con sus instrucciones.
3. Guarda y publica los cambios:

   ```bash
   git add MiProyecto
   git commit -m "Add MiProyecto"
   git push
   ```

Los proyectos pueden definir su propio `.gitignore` y sus instrucciones de
instalación.
