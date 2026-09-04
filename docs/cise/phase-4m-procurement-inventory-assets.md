# Fase 4M — Proveedores, compras, inventario y activos

## Alcance aprobado

Este bloque completa los elementos que no debían quedar pendientes después de
4K y 4L:

- clasificar `Cemento Canal` y crear siete proveedores adicionales;
- registrar inventario inicial para los 44 artículos físicos;
- crear cinco órdenes de compra del proyecto de construcción;
- configurar las cuentas mínimas de inventario y activos;
- crear tres categorías y cinco artículos de activos;
- registrar siete activos operativos con ubicaciones y depreciación.

## Criterio contable

La cuenta nueva `Inventario de Materiales y Herramientas - CYCE` pertenece al
grupo corriente de Inventarios y se configura como cuenta de inventario de la
empresa. La entrada inicial usa como contrapartida la cuenta estándar de ajuste
de inventarios.

Las cuentas existentes de parque vehicular, maquinaria y depreciación acumulada
solo se reclasifican si no tienen movimientos contables. Las categorías usan
línea recta, frecuencia mensual y valor residual del 10 %.

Los activos se registran como activos existentes. Esto crea control operativo,
ubicación, movimiento y calendario de depreciación; no inventa facturas de
adquisición históricas.

## Compras del demo

Las órdenes usan IVA, el proyecto `PROJ-0001` y el centro de costo
`Construcción Estación Nueva Distrito 3 - CYCE`. Cuatro se envían y una queda en
borrador para representar un flujo pendiente de aprobación.

## Seguridad e idempotencia

El script usa Frappe ORM, valida referencias únicas y no crea duplicados al
repetirse. Antes de la aplicación definitiva se generó el respaldo completo
`20260903_154305` en `sites/frontend/private/backups/`.

## Resultado aplicado

- 8 proveedores disponibles; `Cemento Canal` quedó clasificado y se crearon 7.
- Entrada `MAT-STE-2026-00001` enviada con 44 líneas y valor de C$ 2,308,050.00.
- Los 44 artículos físicos tienen cantidad y valoración positiva en su almacén.
- La entrada contable carga Inventario y abona Ajuste de Inventarios por el
  mismo importe, vinculada a `PROJ-0001` y su centro de costo.
- Órdenes `PUR-ORD-2026-00002` a `PUR-ORD-2026-00006`: cuatro enviadas y una
  en borrador, por un total de C$ 4,269,375.00 incluyendo IVA.
- 3 categorías de activos, 5 artículos capitalizables y 3 ubicaciones.
- 7 activos enviados por costo histórico total de C$ 15,730,000.00: dos
  camionetas, retroexcavadora, camión volquete, excavadora y dos compactadoras.
- Los 7 activos tienen movimiento de recepción, depreciación acumulada inicial
  y calendario mensual activo.
- La segunda ejecución terminó sin crear ni modificar registros.
- Dos workers, scheduler, servicios Docker, `ping` y `/desk` quedaron operativos.

## Consulta en ERPNext

- **Proveedor / Supplier**: catálogo de proveedores.
- **Orden de compra / Purchase Order**: referencias `CISE-DEMO-OC-002` a `006`.
- **Entrada de stock / Stock Entry**: `MAT-STE-2026-00001`.
- **Balance de existencias / Stock Balance**: almacenes de obra y herramientas.
- **Activo / Asset**: `ACC-ASS-2026-00001` a `00007`.
- **Calendario de depreciación de activos**: siete calendarios activos.
