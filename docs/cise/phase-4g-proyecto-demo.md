# Fase 4G — Proyecto demostrativo

## Proyecto existente

`Estación Nueva Distrito 3` ya existe. Su identificador fue generado por la
serie estándar `PROJ-.####`; ningún script depende del valor `PROJ-0001`.

Los datos funcionales coinciden con la ficha aprobada, excepto por el
departamento heredado `Ejecución Comercial - CISE`.

El proyecto conserva actividad histórica:

- tres tareas;
- una orden de compra enviada;
- una factura de compra enviada;
- una recepción de compra en borrador;
- costo de compra acumulado de C$150,000.00.

Por trazabilidad no se elimina ni se duplica.

## Normalización aprobada

El proyecto se localiza por `project_name` y se asigna a la unidad operativa
`Gestión de Proyectos de Construcción - CISE`. No se utiliza el nodo agrupador
`Dirección de Operaciones - Construcción - CISE`.

No se modifican estado, prioridad, fechas, costo estimado, tareas, avance ni
documentos contables.

## Respaldo previo

Antes de la normalización se creó el respaldo completo con sello
`20260903_144507` en `sites/frontend/private/backups/`.

## Proyecto de consultoría

El segundo proyecto es independiente del proyecto de construcción y utiliza su
propio identificador generado por la serie estándar.

Ficha aprobada:

- Nombre: `Estudio de Suelos - Estación Nueva Distrito 3`
- Empresa: `CYCE, S.A.`
- Tipo: `Verticales`
- Línea de servicio: `Estudios de Suelos`
- Departamento: `Coordinación de Consultoría - CISE`
- Estado: `Open`
- Prioridad: `High`
- Activo: `Yes`
- Inicio previsto: `2026-07-06`
- Finalización prevista: `2026-10-02`
- Costo estimado: C$450,000.00
- Método de avance: `Task Completion`

Antes de crear este segundo proyecto se generó el respaldo completo con sello
`20260903_144828`.

## Resultado validado

- `PROJ-0001`: proyecto de construcción `Estación Nueva Distrito 3`.
- `PROJ-0002`: proyecto de consultoría `Estudio de Suelos - Estación Nueva
  Distrito 3`.
- El proyecto de consultoría inició con 0 % de avance, sin tareas y sin
  movimientos contables.
- Una segunda ejecución reconoció ambos datos como existentes y no generó
  duplicados.

Las fechas del proyecto de consultoría se ajustaron posteriormente para que el
proyecto permanezca realmente en curso al 2026-09-03.
