# CYCE Viaticos

Aplicación Frappe para controlar viáticos diarios vinculados con asistencia.

La versión 0.5.5 incorpora la estructura V1, las reglas operativas V2, la integración contable V3 y la captura y consulta rápida V4:

- Viático principal con tipos Adelantado y Reposición.
- Detalle por día con cargo, destino, proyecto y referencia de asistencia.
- Registro de ajustes pendientes para períodos posteriores.
- Rol exclusivo `Aprobador de Viaticos`, asignado a `nelly@cise.com`.
- Elegibilidad automática contra Asistencia enviada para el mismo empleado y día.
- Medio día, ausencia, permiso y trabajo desde casa no generan viático.
- Los adelantos futuros quedan pendientes de conciliación hasta registrar asistencia.
- Un adelanto no elegible ya aprobado genera un ajuste para el siguiente viático.
- Aplicación y reversión trazable de saldos de ajustes.
- Los viáticos adelantados generan un anticipo de empleado enviado y sin pagar.
- Las reposiciones generan una solicitud de gasto aprobada contra la cuenta de viáticos.
- La cancelación del viático revierte su documento contable si todavía no tiene pagos.
- El período, monto diario, destino y proyecto permiten generar automáticamente todos los días calendario.
- Los montos se precargan de forma uniforme y cada día puede modificarse antes de guardar.
- Regenerar un período con detalles existentes requiere confirmación porque reemplaza las filas actuales.
- Los totales del borrador se recalculan al generar, editar o eliminar días.
- El estado contable se consulta desde el listado y no ocupa espacio durante la captura.
- Plantillas reutilizables permiten precargar tipo, moneda, monto, destino y proyecto.
- La planilla multiempleado excluye a Augusto y genera viáticos individuales de forma transaccional.
- Nelly es la única persona autorizada para aprobar o cancelar la planilla y sus viáticos.
- Tres reportes permiten consultar un viático específico, el listado general y el detalle diario.
- El formato `Comprobante de Viatico` permite imprimir cada documento individual.

Los pagos bancarios se implementarán únicamente en una etapa posterior aprobada por separado.
