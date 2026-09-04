# Fase 4N — personal CYCE

## Fuente

Se inspeccionó `LISTADO SENCILLO DEL PERSONAL.xlsx` sin modificar el original.
El archivo contiene 43 filas y 42 personas normalizadas. Juan Loáisiga aparece
dos veces con referencias a Hialeah y Milagro de Dios, por lo que se conserva
como una sola persona con dos referencias de proyecto.

María Andrade se vincula con el Employee existente `HR-EMP-00001`, María Nelly
Andrade. Se conserva la decisión funcional previa de asignarla a Gerencia
General y no se crea un duplicado.

## Cargos

Se reutilizaron los cargos existentes Gerente General, Gestor de Calidad,
Asistente Administrativo y Gerente de Proyecto. Se crearon 15 cargos:

- Asistente Contable
- Ayudante de Obra
- Bodeguero
- Cadenero
- Calculista
- Conductor
- Fiscal de Obra
- Maestro de Obra
- Operador de Excavadora
- Operador de Retroexcavadora
- Operador de Volquete
- Residente de Proyecto
- Topógrafo
- Técnico de Laboratorio
- Vigilante

## Datos provisionales autorizados

El DocType Employee exige `gender`, `date_of_birth` y `date_of_joining`. El
archivo fuente no contiene esos datos para las 41 personas nuevas. Por
instrucción del usuario se aplican los siguientes valores provisionales:

- gender inferido a partir del nombre de la persona;
- date_of_birth: `1980-01-01`;
- date_of_joining: `2026-01-01`.

Estos valores deben revisarse y sustituirse manualmente cuando CYCE entregue la
información real. El script `scripts/cise/phase4n_employees.py` crea los
Employee mediante Frappe ORM y reutiliza a Nelly.

## Resultado aplicado

Se crearon 41 Employee nuevos, desde `HR-EMP-00002` hasta `HR-EMP-00042`, y se
reutilizó `HR-EMP-00001` para María Nelly Andrade. Los 42 Employee quedaron
activos, con cargo y departamento normalizados. Ninguno de los 41 registros
nuevos fue vinculado a un User.

La validación idempotente confirmó:

- 42 personas resueltas y 42 identificadores únicos;
- cero personas faltantes y cero diferencias de datos;
- 7 registros Female y 35 Male;
- un solo Employee para Juan Loáisiga;
- Nelly permanece como `HR-EMP-00001` en Gerencia General.

## Exclusiones

Este bloque no crea Users, Salary Structure, Salary Structure Assignment,
Payroll Entry ni Salary Slip. Las referencias de proyecto del archivo se
conservan como contexto y no se convierten automáticamente en relaciones de
Project.

Antes y después de la carga permanecieron: cero Salary Structure Assignment,
un Payroll Entry preexistente y cero Salary Slip. El bloque no creó ni modificó
configuración de nómina.

## Respaldo

Antes de crear los Designation se generó el respaldo completo
`20260904_102855` del site `frontend`.

Inmediatamente antes de crear los Employee se generó el respaldo completo
`20260904_105245` del site `frontend`, incluyendo base de datos y archivos.
