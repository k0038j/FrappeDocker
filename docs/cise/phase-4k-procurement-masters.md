# Fase 4K — Base maestra para compras

## Alcance aplicado

Este bloque prepara catálogos para compras, inventario, proyectos y reportes.
No crea proveedores, artículos, activos ni órdenes de compra.

Se incorporan:

- grupos de proveedores por actividad;
- grupos de artículos para materiales, herramientas, servicios y activos;
- unidades comerciales faltantes;
- almacenes operativos;
- centros de costo por proyecto;
- vínculo de los dos proyectos con sus centros de costo.

## Conservación de datos existentes

No se modifica la orden enviada `PUR-ORD-2026-00001`, el proveedor `Cemento
Canal` ni el artículo `987654321`. Sus correcciones requieren un bloque
específico porque ya tienen documentos contables y de compra relacionados.

El grupo aislado `Maquinaria` se reutiliza como `Activos de Maquinaria y
Transporte` solamente después de comprobar que no contiene artículos ni
subgrupos.

## Almacenes nuevos

- Bodega Central de Materiales - CISE
- Bodega de Obra Estación Nueva Distrito 3 - CISE
- Almacén de Herramientas - CISE
- Patio de Maquinaria y Equipos - CISE

## Centros de costo nuevos

- Operaciones - CISE
  - Construcción Estación Nueva Distrito 3 - CISE
  - Consultoría Estudio de Suelos - CISE

## Exclusiones

Las cuentas de maquinaria, parque vehicular y depreciación no se modifican en
este bloque. Deben resolverse con las categorías de activos antes de registrar
camionetas, camiones, retroexcavadoras, excavadoras o equipos menores.

## Respaldo previo

Antes de aplicar esta estructura se creó el respaldo completo con sello
`20260903_151735` en `sites/frontend/private/backups/`.

## Resultado validado

- 8 grupos de proveedores creados.
- 24 grupos de artículos creados o normalizados.
- 5 unidades comerciales creadas.
- 4 almacenes operativos creados.
- 3 centros de costo creados.
- Los dos proyectos quedaron vinculados a centros de costo independientes.
- La orden histórica permaneció sin cambios.
- Una segunda ejecución no generó duplicados.
