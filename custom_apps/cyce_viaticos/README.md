# CYCE Viaticos

Aplicación Frappe para controlar viáticos diarios vinculados con asistencia.

La versión 0.3.3 incorpora la estructura V1, las reglas operativas V2 y la integración contable V3:

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

Los pagos bancarios se implementarán únicamente en una etapa posterior aprobada por separado.
