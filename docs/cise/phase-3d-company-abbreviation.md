# Fase 3D — abreviatura de CYCE

## Decisión aplicada

La empresa conserva el nombre `CYCE, S.A.` y cambia únicamente su abreviatura
técnica de `CISE` a `CYCE`. No se modifican nombres base, códigos contables,
jerarquías, importes ni documentos transaccionales.

## Respaldo

Antes del cambio se generó el respaldo completo del site `frontend`:

- base: `20260904_083331-frontend-database.sql.gz`;
- configuración: `20260904_083331-frontend-site_config_backup.json`;
- archivos públicos y privados con el mismo prefijo.

Los archivos permanecen en `sites/frontend/private/backups` dentro del volumen
persistente de sitios.

## Migración

El script `scripts/cise/phase3d_company_abbreviation.py` realiza una auditoría
sin cambios por defecto. Con `apply=True`:

1. elimina solamente los dos Property Setters temporales usados para ocultar el
   identificador completo de Account;
2. actualiza `Company.abbr` mediante la API de base de datos de Frappe, necesaria
   porque el campo es `set_only_once`;
3. usa `rename_doc` para actualizar identificadores y enlaces de Account,
   Department, Warehouse, Cost Center y las plantillas fiscales;
4. verifica saldos, estructura contable, conteos, árboles y ausencia del sufijo
   anterior;
5. confirma la transacción únicamente después de superar todas las validaciones.

## Resultado validado

- Company.abbr: `CYCE`.
- Account: 390 identificadores con sufijo `- CYCE`.
- Department: 30.
- Warehouse: 9.
- Cost Center: 5.
- Plantillas fiscales: 3.
- Asientos GL no cancelados: 19.
- Débitos y créditos: C$ 2,639,780.90 por cada lado.
- Property Setters temporales: ausentes.

El árbol de Department ya contenía 12 avisos de intervalos antes de esta tarea.
La migración exige que esos avisos preexistentes permanezcan exactamente iguales;
no intenta reparar ni remodelar el organigrama.

