# Fase 4N — usuarios de sistema CYCE

## Alcance aprobado

La tabla entregada autoriza siete usuarios de sistema. María Nelly Andrade ya
estaba vinculada a `nelly@cise.com`, por lo que se conserva esa cuenta y sus
roles actuales. Se crean únicamente las seis cuentas faltantes.

Los 35 Employee marcados como `NO` permanecen sin User. No se crean empleados,
proveedores, tipos de empleo, salarios ni documentos de nómina en este bloque.

## Cuentas y acceso mínimo

| Employee | Usuario | Roles funcionales mínimos |
| --- | --- | --- |
| HR-EMP-00002 | augusto.garcia@cise.com | Employee, Employee Self Service, Analytics |
| HR-EMP-00001 | nelly@cise.com | Se conservan roles existentes |
| HR-EMP-00003 | marbel.canales@cise.com | Employee, Employee Self Service, Quality Manager, Projects User |
| HR-EMP-00004 | maria.centeno@cise.com | Employee, Employee Self Service, Purchase User |
| HR-EMP-00005 | anshley.palacios@cise.com | Employee, Employee Self Service, Accounts User |
| HR-EMP-00012 | junieth.luna@cise.com | Employee, Employee Self Service, Projects User |
| HR-EMP-00013 | ingrid.paz@cise.com | Employee, Employee Self Service, Projects User |

Las cuentas se crean habilitadas como `System User`, con correo de bienvenida
desactivado y sin una contraseña provisional inventada. El administrador debe
establecer o restablecer la contraseña cuando confirme las direcciones reales.

Los permisos detallados por proyecto, avalúo, cuentas bancarias y campos
sensibles requieren una fase posterior de roles y User Permissions. Los roles
de este bloque son mínimos y no sustituyen ese diseño.

## Implementación

El script `scripts/cise/phase4n_system_users.py` utiliza Frappe ORM, valida
Employee, correos y roles antes de escribir, vincula `Employee.user_id` y puede
ejecutarse repetidamente sin duplicar usuarios.

## Resultado aplicado

Se conservaron `nelly@cise.com` y sus roles existentes. Se crearon y vincularon
las otras seis cuentas autorizadas. La validación final confirmó:

- 7 usuarios autorizados y 7 resueltos;
- cero cuentas faltantes y cero diferencias de configuración;
- exactamente 7 Employee CYCE vinculados a User;
- cero vínculos de User entre los 35 Employee marcados como `NO`;
- User Permission para la empresa `CYCE, S.A.` y para el Employee propio de
  cada cuenta nueva;
- segunda ejecución idempotente sin duplicados.

Los conteos de nómina permanecieron sin cambios: cero Salary Structure
Assignment, un Payroll Entry preexistente y cero Salary Slip.

## Respaldo

Inmediatamente antes de crear las cuentas se generó el respaldo completo
`20260904_120503` del site `frontend`, incluyendo base de datos y archivos.
