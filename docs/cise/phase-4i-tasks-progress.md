# Fase 4I — Tareas y avance de consultoría

## Alcance

Esta configuración se aplica únicamente al proyecto de consultoría
`Estudio de Suelos - Estación Nueva Distrito 3`. El proyecto de construcción y
sus tareas existentes no se modifican.

## Usuario funcional

- Nombre: `Coordinación de Consultoría`
- Usuario: `coordinacion.consultoria@cise.com`
- Tipo: System User
- Rol: `Projects User`
- Correo de bienvenida: deshabilitado
- Contraseña: no se almacena en el repositorio

Se utiliza una cuenta funcional en lugar de inventar una persona o un Employee.
El usuario se vincula a la tabla de usuarios del proyecto y se asigna a las
tareas mediante la funcionalidad estándar `Assign To`.

La fila del usuario en el proyecto se marca con `welcome_email_sent = 1` para
evitar que ERPNext intente enviar una invitación: este entorno local no tiene
configurada una cuenta de correo saliente.

## Fechas del proyecto

- Inicio previsto: 2026-07-06
- Finalización prevista: 2026-10-02

Al 2026-09-03 el proyecto está realmente en curso.

## Tareas

1. Planificación y recopilación de información — Completed
2. Trabajo de campo y toma de muestras — Completed
3. Ensayos y análisis geotécnico — Completed
4. Revisión y entrega final — Working

Las tareas son hojas y mantienen dependencias lineales. Todas se asignan al
usuario funcional de Coordinación de Consultoría.

## Cálculo de avance

El método del proyecto permanece `Task Completion`. ERPNext calcula tres tareas
completadas entre cuatro tareas totales:

`3 / 4 × 100 = 75 %`

El script no escribe directamente el porcentaje del proyecto.

## Respaldo previo

Antes de crear el usuario y las tareas se generó el respaldo completo con sello
`20260903_145620` en `sites/frontend/private/backups/`.

## Resultado validado

- `TASK-2026-00004`: Planificación y recopilación de información — Completed
- `TASK-2026-00005`: Trabajo de campo y toma de muestras — Completed
- `TASK-2026-00006`: Ensayos y análisis geotécnico — Completed
- `TASK-2026-00007`: Revisión y entrega final — Working
- Avance calculado de `PROJ-0002`: 75 %
- Avance conservado de `PROJ-0001`: 33.33 %

Las asignaciones de las tareas completadas quedaron cerradas automáticamente;
la asignación de la tarea en curso permanece abierta. Una segunda ejecución no
creó usuarios, tareas, dependencias ni asignaciones duplicadas.
