import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "D:/App/ProyectoERPNext/FrappeDocker/outputs/payroll-distribution-20260910";
const outputPath = `${outputDir}/plantilla_distribucion_nomina_inss_2026.xlsx`;
const previewPath = `${outputDir}/preview_distribucion_nomina.png`;
const fontFamily = "Arial";
const employees = [
  {
    "employee": "HR-EMP-00001",
    "employeeName": "María Nelly Andrade",
    "company": "CYCE, S.A.",
    "department": "Gerencia Comercial - CYCE",
    "designation": "Gerente Comercial",
    "employmentType": "Contract",
    "dateOfJoining": "2021-01-01",
    "branch": "Managua",
    "salaryCurrency": "NIO",
    "ctc": 60000
  },
  {
    "employee": "HR-EMP-00002",
    "employeeName": "Augusto García",
    "company": "CYCE, S.A.",
    "department": "Gerencia General - CYCE",
    "designation": "Gerente General",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00003",
    "employeeName": "Marbel Canales",
    "company": "CYCE, S.A.",
    "department": "Gestión de Calidad - CYCE",
    "designation": "Gestor de Calidad",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00004",
    "employeeName": "María Centeno",
    "company": "CYCE, S.A.",
    "department": "Administración - CYCE",
    "designation": "Asistente Administrativo",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00005",
    "employeeName": "Anshley Palacios",
    "company": "CYCE, S.A.",
    "department": "Contabilidad - CYCE",
    "designation": "Asistente Contable",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00006",
    "employeeName": "Julio Benavides",
    "company": "CYCE, S.A.",
    "department": "Gestión de Proyectos de Construcción - CYCE",
    "designation": "Gerente de Proyecto",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00007",
    "employeeName": "Javier Solórzano",
    "company": "CYCE, S.A.",
    "department": "Gestión de Proyectos de Construcción - CYCE",
    "designation": "Residente de Proyecto",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00008",
    "employeeName": "Edwin Gutiérrez",
    "company": "CYCE, S.A.",
    "department": "Gestión de Proyectos de Construcción - CYCE",
    "designation": "Residente de Proyecto",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00009",
    "employeeName": "Erick González",
    "company": "CYCE, S.A.",
    "department": "Gestión de Proyectos de Construcción - CYCE",
    "designation": "Residente de Proyecto",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00010",
    "employeeName": "Eduardo Medina",
    "company": "CYCE, S.A.",
    "department": "Gestión de Proyectos de Construcción - CYCE",
    "designation": "Residente de Proyecto",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00011",
    "employeeName": "Rudy Miranda",
    "company": "CYCE, S.A.",
    "department": "Gestión de Proyectos de Construcción - CYCE",
    "designation": "Residente de Proyecto",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00012",
    "employeeName": "Junieth Luna",
    "company": "CYCE, S.A.",
    "department": "Gestión de Proyectos de Construcción - CYCE",
    "designation": "Fiscal de Obra",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00013",
    "employeeName": "Ingrid Paz",
    "company": "CYCE, S.A.",
    "department": "Gestión de Proyectos de Construcción - CYCE",
    "designation": "Calculista",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00014",
    "employeeName": "Fernando Castillo",
    "company": "CYCE, S.A.",
    "department": "Gestión de Calidad - CYCE",
    "designation": "Técnico de Laboratorio",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00015",
    "employeeName": "Alejandro Gómez",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Topógrafo",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00016",
    "employeeName": "Óscar Silva",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Topógrafo",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00017",
    "employeeName": "Brayan López",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Cadenero",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00018",
    "employeeName": "David Montenegro",
    "company": "CYCE, S.A.",
    "department": "Maquinaria y Equipos - CYCE",
    "designation": "Operador de Retroexcavadora",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00019",
    "employeeName": "Michael Escalante",
    "company": "CYCE, S.A.",
    "department": "Maquinaria y Equipos - CYCE",
    "designation": "Operador de Retroexcavadora",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00020",
    "employeeName": "Carlos Miranda",
    "company": "CYCE, S.A.",
    "department": "Maquinaria y Equipos - CYCE",
    "designation": "Operador de Excavadora",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00021",
    "employeeName": "Luis Espinoza",
    "company": "CYCE, S.A.",
    "department": "Maquinaria y Equipos - CYCE",
    "designation": "Operador de Volquete",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00022",
    "employeeName": "José Rodríguez",
    "company": "CYCE, S.A.",
    "department": "Maquinaria y Equipos - CYCE",
    "designation": "Operador de Volquete",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00023",
    "employeeName": "Miguel Blandón",
    "company": "CYCE, S.A.",
    "department": "Maquinaria y Equipos - CYCE",
    "designation": "Conductor",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00024",
    "employeeName": "Larry Rosales",
    "company": "CYCE, S.A.",
    "department": "Maquinaria y Equipos - CYCE",
    "designation": "Conductor",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00025",
    "employeeName": "Wiliam Cano",
    "company": "CYCE, S.A.",
    "department": "Maquinaria y Equipos - CYCE",
    "designation": "Conductor",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00026",
    "employeeName": "Wiston Jarquín",
    "company": "CYCE, S.A.",
    "department": "Maquinaria y Equipos - CYCE",
    "designation": "Conductor",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00027",
    "employeeName": "Porfirio Membreño",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Maestro de Obra",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00028",
    "employeeName": "Dionisio González",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Maestro de Obra",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00029",
    "employeeName": "Jhon Largaespada",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Maestro de Obra",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00030",
    "employeeName": "Halmar Cárcamo",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Bodeguero",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00031",
    "employeeName": "Amanda Alarcón",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Vigilante",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00032",
    "employeeName": "Juan Loáisiga",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Vigilante",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00033",
    "employeeName": "Abraham Herrera",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Vigilante",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00036",
    "employeeName": "César",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Ayudante de Obra",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00037",
    "employeeName": "Erlin Mercado",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Ayudante de Obra",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00038",
    "employeeName": "Isacc Sirios",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Ayudante de Obra",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00040",
    "employeeName": "Pablo",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Ayudante de Obra",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00041",
    "employeeName": "Carlos Delgado",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Ayudante de Obra",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  },
  {
    "employee": "HR-EMP-00042",
    "employeeName": "Donald Fonseca",
    "company": "CYCE, S.A.",
    "department": "Operaciones de Obra - CYCE",
    "designation": "Ayudante de Obra",
    "employmentType": "",
    "dateOfJoining": "2026-01-01",
    "branch": "",
    "salaryCurrency": "",
    "ctc": 0
  }
];

await fs.mkdir(outputDir, { recursive: true });

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Distribución");
sheet.showGridLines = false;
sheet.tabColor = "#1F4E78";

sheet.getRange("A2").values = [["Distribución de empleados en nóminas INSS"]];
sheet.getRange("A2").format = {
  font: { name: fontFamily, size: 15, bold: true, color: "#1F1F1F" },
};
sheet.getRange("A3").values = [["Complete sólo las celdas amarillas. Use 0 cuando un acumulado fiscal no exista."]];
sheet.getRange("A3").format = {
  font: { name: fontFamily, size: 10, italic: true, color: "#595959" },
};
sheet.getRange("A4").values = [["Fuente: ERPNext, sitio frontend. Empleados activos consultados el 10/09/2026."]];
sheet.getRange("A4").format = {
  font: { name: fontFamily, size: 9, italic: true, color: "#7F7F7F" },
};

sheet.getRange("A5:N5").values = [[
  "Empleados activos", employees.length, null,
  "Filas completas", null, null,
  "Pendientes", null, null,
  "Mensual INSS", null, null,
  "Quincenal INSS", null
]];
sheet.getRange("E5").formulas = [["=COUNTIFS($O$9:$O$47,\"Completo\")"]];
sheet.getRange("H5").formulas = [["=B5-E5"]];
sheet.getRange("K5").formulas = [["=COUNTIFS($H$9:$H$47,\"Nomina Mensual INSS\")"]];
sheet.getRange("N5").formulas = [["=COUNTIFS($H$9:$H$47,\"Nomina Quincenal INSS\")"]];
for (const labelCell of ["A5", "D5", "G5", "J5", "M5"]) {
  sheet.getRange(labelCell).format = {
    fill: "#D9EAF7",
    font: { name: fontFamily, size: 10, bold: true, color: "#1F1F1F" },
    borders: { preset: "outside", style: "thin", color: "#9EADBA" },
  };
}
for (const valueCell of ["B5", "E5", "H5", "K5", "N5"]) {
  sheet.getRange(valueCell).format = {
    fill: "#FFFFFF",
    font: { name: fontFamily, size: 11, bold: true, color: "#1F4E78" },
    horizontalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: "#9EADBA" },
    numberFormat: "0",
  };
}

sheet.getRange("A6").values = [["Amarillo: completar. Azul: cálculo automático. Blanco: dato de ERPNext para referencia."]];
sheet.getRange("A6").format = {
  font: { name: fontFamily, size: 9, italic: true, color: "#595959" },
};

const headers = [[
  "Código empleado",
  "Nombre del empleado",
  "Departamento",
  "Cargo",
  "Tipo de empleo actual",
  "Fecha de ingreso",
  "Sucursal",
  "Grupo de nómina",
  "Salario base mensual (NIO)",
  "Base ERPNext por ciclo (NIO)",
  "Fecha de vigencia",
  "Renta gravable acumulada 2026 (NIO)",
  "IR retenido acumulado 2026 (NIO)",
  "Observaciones",
  "Estado de fila"
]];
sheet.getRange("A8:O8").values = headers;
sheet.getRange("A8:O8").format = {
  fill: "#1F4E78",
  font: { name: fontFamily, size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: {
    insideVertical: { style: "thin", color: "#FFFFFF" },
    bottom: { style: "medium", color: "#17365D" },
  },
  rowHeight: 34,
};

const sourceRows = employees.map((e) => [
  e.employee,
  e.employeeName,
  e.department,
  e.designation,
  e.employmentType,
  new Date(`${e.dateOfJoining}T00:00:00`),
  e.branch,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
  null,
]);
sheet.getRange("A9:O47").values = sourceRows;

sheet.getRange("J9").formulas = [[
  '=IF(H9="","",IF(H9="Nomina Quincenal INSS",I9/2,I9))'
]];
sheet.getRange("J9:J47").fillDown();

sheet.getRange("O9").formulas = [[
  '=IF(H9="","Falta grupo",IF(I9="","Falta salario",IF(K9="","Falta fecha",IF(K9<F9,"Fecha anterior al ingreso",IF(K9>DATE(2026,12,31),"Fecha fuera de 2026",IF(AND(K9>DATE(2026,1,1),COUNTBLANK(L9:M9)>0),"Faltan acumulados","Completo"))))))'
]];
sheet.getRange("O9:O47").fillDown();

const body = sheet.getRange("A9:O47");
body.format.font = { name: fontFamily, size: 10, color: "#1F1F1F" };
body.format.verticalAlignment = "center";
body.format.rowHeight = 20;
sheet.getRange("F9:F47").format.numberFormat = "dd/mm/yyyy";
sheet.getRange("F9:F47").format.horizontalAlignment = "center";
sheet.getRange("I9:J47").format.numberFormat = "#,##0.00";
sheet.getRange("K9:K47").format.numberFormat = "dd/mm/yyyy";
sheet.getRange("K9:K47").format.horizontalAlignment = "center";
sheet.getRange("L9:M47").format.numberFormat = "#,##0.00";
sheet.getRange("I9:J47").format.horizontalAlignment = "right";
sheet.getRange("L9:M47").format.horizontalAlignment = "right";

sheet.getRange("H9:I47").format.fill = "#FFF2CC";
sheet.getRange("K9:N47").format.fill = "#FFF2CC";
sheet.getRange("J9:J47").format.fill = "#DDEBF7";
sheet.getRange("O9:O47").format.fill = "#F2F2F2";
sheet.getRange("H9:N47").format.borders = {
  insideHorizontal: { style: "thin", color: "#E7E6E6" },
};

sheet.getRange("H9:H47").dataValidation = {
  rule: {
    type: "list",
    values: ["Nomina Mensual INSS", "Nomina Quincenal INSS"],
  },
};

sheet.getRange("O9:O47").conditionalFormats.add("containsText", {
  text: "Completo",
  format: {
    fill: "#E2F0D9",
    font: { bold: true, color: "#375623" },
  },
});
sheet.getRange("O9:O47").conditionalFormats.add("containsText", {
  text: "Falta",
  format: {
    fill: "#FCE4D6",
    font: { bold: true, color: "#C00000" },
  },
});
sheet.getRange("O9:O47").conditionalFormats.add("containsText", {
  text: "Fecha",
  format: {
    fill: "#FCE4D6",
    font: { bold: true, color: "#C00000" },
  },
});

const table = sheet.tables.add("A8:O47", true, "DistribucionNominaTable");
table.style = "TableStyleMedium2";
table.showBandedColumns = false;
table.showFilterButton = true;

const widths = {
  A: 17, B: 25, C: 42, D: 27, E: 20, F: 14, G: 16, H: 24,
  I: 21, J: 22, K: 16, L: 26, M: 25, N: 28, O: 24,
};
for (const [column, width] of Object.entries(widths)) {
  sheet.getRange(`${column}1:${column}47`).format.columnWidth = width;
}
sheet.getRange("B9:E47").format.wrapText = false;
sheet.getRange("N9:N47").format.wrapText = false;
sheet.freezePanes.freezeRows(8);
sheet.freezePanes.freezeColumns(2);

workbook.recalculate();

// Prueba funcional temporal: un caso mensual y uno quincenal.
sheet.getRange("H9:I10").values = [
  ["Nomina Mensual INSS", 20000],
  ["Nomina Quincenal INSS", 20000],
];
sheet.getRange("K9:N10").values = [
  [new Date("2026-01-01T00:00:00"), null, null, null],
  [new Date("2026-09-01T00:00:00"), 0, 0, null],
];
workbook.recalculate();
const functionalCheck = await workbook.inspect({
  kind: "table",
  range: "Distribución!H9:O10",
  include: "values,formulas",
  tableMaxRows: 2,
  tableMaxCols: 8,
  maxChars: 4000,
});
console.log("FUNCTIONAL_CHECK");
console.log(functionalCheck.ndjson);

// Restaurar las entradas para entregar una plantilla limpia.
sheet.getRange("H9:I10").values = [[null, null], [null, null]];
sheet.getRange("K9:N10").values = [
  [null, null, null, null],
  [null, null, null, null],
];
workbook.recalculate();

const check = await workbook.inspect({
  kind: "table",
  range: "Distribución!A2:O15",
  include: "values,formulas",
  tableMaxRows: 15,
  tableMaxCols: 15,
  maxChars: 12000,
});
console.log("KEY_RANGE");
console.log(check.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log("FORMULA_ERRORS");
console.log(errors.ndjson);

const preview = await workbook.render({
  sheetName: "Distribución",
  range: "A1:O20",
  scale: 1.3,
  format: "png",
});
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const saved = await FileBlob.load(outputPath);
const imported = await SpreadsheetFile.importXlsx(saved);
const savedCheck = await imported.inspect({
  kind: "table",
  range: "Distribución!A5:O12",
  include: "values,formulas",
  tableMaxRows: 10,
  tableMaxCols: 15,
  maxChars: 8000,
});
console.log("SAVED_FILE_CHECK");
console.log(savedCheck.ndjson);
console.log(`OUTPUT=${outputPath}`);
console.log(`PREVIEW=${previewPath}`);
