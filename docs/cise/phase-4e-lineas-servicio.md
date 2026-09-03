# Fase 4E — Líneas de Servicio

## Decisión funcional

Las líneas de servicio de consultoría se modelan en un maestro independiente y
se relacionan con `Project` mediante un campo Link. No se mezclan con `Project
Type`, `Department`, `Designation`, `Role` ni `Cost Center`.

El campo es opcional para permitir proyectos exclusivamente constructivos.

## Maestro inicial

- Diseños
- Topografía
- Asistencia Técnica
- Estudios de Suelos
- Supervisión de Obra

## Personalización

- DocType personalizado interno: `CISE Service Line`
- Nombre visible en español: `Línea de Servicio`
- Campo en Project: `custom_linea_de_servicio`
- Etiqueta: `Línea de Servicio`
- Tipo: Link a `CISE Service Line`
- Ubicación: después de `project_type`
- Disponible como filtro estándar

Los usuarios de proyectos pueden consultar y seleccionar registros, pero no
pueden crearlos, editarlos ni eliminarlos. Los roles `Projects Manager` y
`System Manager` pueden mantener el maestro. La importación masiva permanece
deshabilitada.

## Aplicación idempotente

El nombre técnico usa caracteres ASCII porque Frappe v16 no admite tildes en el
nombre de un DocType. Una traducción controlada muestra `Línea de Servicio` en
español.

El script `scripts/cise/phase4e_service_lines.py` comprueba la estructura y la
traducción antes de insertar. Si encuentra una personalización incompatible,
cancela la operación sin sobrescribirla.

Copiar temporalmente el script al paquete de Frappe dentro del contenedor y
ejecutarlo mediante Bench para que se inicialice el contexto del site:

```console
docker compose -p frappe_docker cp scripts/cise/phase4e_service_lines.py backend:/home/frappe/frappe-bench/apps/frappe/frappe/phase4e_service_lines.py
docker compose -p frappe_docker exec -T backend bench --site frontend execute frappe.phase4e_service_lines.execute
```

## Respaldo previo de esta ejecución

- Fecha: 2026-09-03 12:00
- Base de datos: `20260903_120021-frontend-database.sql.gz`
- Configuración: `20260903_120021-frontend-site_config_backup.json`
- Archivos públicos: `20260903_120021-frontend-files.tar`
- Archivos privados: `20260903_120021-frontend-private-files.tar`
- Ubicación dentro del volumen del site: `sites/frontend/private/backups/`

Antes de corregir los permisos predeterminados del rol `Projects User` se creó
un segundo respaldo completo con sello `20260903_120615` en la misma ubicación.

## Validación funcional

1. Buscar `Línea de Servicio` para consultar el maestro.
2. Abrir un proyecto y comprobar el campo después de `Tipo de proyecto`.
3. Confirmar que Tipo de proyecto y Línea de Servicio admiten filtros separados.

El proyecto `PROJ-0001` no recibe una línea automáticamente; requiere una
decisión funcional sobre si corresponde a consultoría.
