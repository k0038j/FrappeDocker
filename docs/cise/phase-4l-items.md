# Fase 4L — Catálogo de materiales, EPP, herramientas y servicios

## Estado

Aplicado y validado en el site `frontend` el 3 de septiembre de 2026.

## Alcance aprobado

- 49 artículos en total.
- 44 artículos físicos controlados por inventario.
- 5 servicios no almacenables.
- Materiales, consumibles y EPP con almacén predeterminado de obra.
- Herramientas con almacén predeterminado de herramientas.
- Servicios con la cuenta de gasto `Costo de Servicios - CYCE`.
- Sin lotes, números de serie ni activos fijos en este bloque.

## Normalización del cemento histórico

El artículo `987654321` se renombra mediante la función estándar de Frappe a
`MAT-CEM-001`. Se conserva `Unit` como unidad de inventario porque existen
documentos enviados. Se configura `Saco` como unidad de compra con factor 1:1.

Antes y después se comprueban los documentos históricos, sus importes, estados
y vínculos. No se modifica directamente ninguna tabla de MariaDB.

## Exclusiones

Este bloque no crea proveedores, órdenes de compra, existencias iniciales ni
activos. Camionetas, retroexcavadoras, camiones volquete y excavadoras se
resolverán con categorías y cuentas de activos en la Fase 4M.

## Respaldo previo

Respaldo completo `20260903_152532` en
`sites/frontend/private/backups/`.

## Resultado validado

- Se renombró `987654321` a `MAT-CEM-001` mediante Frappe.
- Se crearon los otros 48 artículos aprobados.
- El catálogo contiene exactamente 49 registros: 44 físicos y 5 servicios.
- Los 44 artículos físicos tienen el almacén aprobado y siguen FIFO global.
- Los 5 servicios no manejan inventario y usan `Costo de Servicios - CYCE`.
- El cemento conserva `Unit` como unidad de inventario y usa `Saco` 1:1 para compra.
- No existen movimientos de inventario históricos del cemento.
- `PUR-ORD-2026-00001` permanece enviada, por C$ 172,500.00 y pendiente de recibir.
- `ACC-PINV-2026-00001` permanece enviada y vencida, por C$ 172,500.00.
- Las dos filas históricas ahora apuntan a `MAT-CEM-001` sin cambiar cantidad,
  tarifa ni importe.
- Una segunda ejecución no creó duplicados ni alteró registros.
- Scheduler, dos workers, servicios Docker y la respuesta web quedaron operativos.

## Consulta en ERPNext

Usar la barra de búsqueda y abrir **Artículo / Item**. Los códigos pueden
filtrarse por los prefijos `MAT-`, `EPP-`, `HER-` y `SRV-`. El cemento se puede
abrir directamente con el código `MAT-CEM-001`.
