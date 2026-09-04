# Fase 3E — plan de cuentas CYCE

## Fuente y alcance

El catálogo se construyó a partir de `nomenclatura de cuentas contables de
cyce.pdf`. Se conservaron la estructura, los códigos y los nombres entregados
por el cliente. El recurso reproducible es
`resources/cise/chart_of_accounts_cyce.json`.

## Resultado

- 154 cuentas numeradas del catálogo CYCE.
- Cuatro cuentas de mayor tipo Bank: 1121, 1122, 1123 y 1124.
- El plan anterior de ERPNext se conserva bajo cinco grupos `LEGACY ERP (NO
  USAR)` para no romper movimientos históricos.
- Los valores predeterminados de empresa, plantillas de IVA, Items y categorías
  de activos apuntan al catálogo numerado.
- Las órdenes demo enviadas fueron canceladas y enmendadas sin cambiar sus
  totales; la orden histórica totalmente facturada quedó cerrada.
- Todos los identificadores generados por empresa terminan en `- CYCE`.

## Reproducibilidad

El script `scripts/cise/phase3e_chart_of_accounts.py` es idempotente y usa el
ORM de Frappe. Antes de insertar valida duplicados, padres y colisiones. No crea
Property Setters visuales ni elimina cuentas con historia.

El Excel entregable contiene cinco hojas: Resumen, Catalogo CYCE, Cuentas
bancarias, Equivalencias y Leyenda. Las celdas de color señalan únicamente
cuentas técnicas o propuestas de reestructuración para revisión con el cliente.

