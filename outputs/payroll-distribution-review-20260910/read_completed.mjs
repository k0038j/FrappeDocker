import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/Admin/Downloads/plantilla_distribucion_nomina_inss_2026_completada.xlsx";
const previewPath = "D:/App/ProyectoERPNext/FrappeDocker/outputs/payroll-distribution-review-20260910/preview_completed.png";

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const overview = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 6000,
  tableMaxRows: 4,
  tableMaxCols: 8,
});
console.log("OVERVIEW");
console.log(overview.ndjson);

const sheet = workbook.worksheets.getItem("Distribución");
workbook.recalculate();

const headers = sheet.getRange("A8:O8").values[0];
const values = sheet.getRange("A9:O47").values;
const formulas = sheet.getRange("A9:O47").formulas;
const allowedGroups = new Set(["Nomina Mensual INSS", "Nomina Quincenal INSS"]);

function isBlank(value) {
  return value === null || value === undefined || value === "";
}

function excelDateToIso(value) {
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (typeof value === "number") {
    const epoch = Date.UTC(1899, 11, 30);
    return new Date(epoch + value * 86400000).toISOString().slice(0, 10);
  }
  if (typeof value === "string" && value) {
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.valueOf())) return parsed.toISOString().slice(0, 10);
  }
  return null;
}

const records = values.map((row, index) => ({
  row: index + 9,
  employee: row[0],
  employeeName: row[1],
  department: row[2],
  designation: row[3],
  group: row[7],
  monthlyBase: row[8],
  cycleBase: row[9],
  effectiveDate: excelDateToIso(row[10]),
  taxableYtd: row[11],
  taxWithheldYtd: row[12],
  notes: row[13],
  status: row[14],
  cycleFormula: formulas[index][9],
  statusFormula: formulas[index][14],
}));

const duplicateCodes = records
  .map((record) => record.employee)
  .filter((code, index, all) => code && all.indexOf(code) !== index);

const excluded = records.find(
  (record) => record.employee === "HR-EMP-00002" || record.employeeName === "Augusto García",
);
if (!excluded) throw new Error("No se encontró a Augusto García en la plantilla.");

const issues = [];
for (const record of records) {
  if (record.employee === excluded.employee) continue;
  if (!allowedGroups.has(record.group)) issues.push({ employee: record.employee, issue: "Grupo inválido o vacío" });
  if (typeof record.monthlyBase !== "number" || record.monthlyBase <= 0) {
    issues.push({ employee: record.employee, issue: "Salario base mensual inválido" });
  }
  if (!record.effectiveDate) issues.push({ employee: record.employee, issue: "Fecha de vigencia vacía o inválida" });
  if (record.effectiveDate && record.effectiveDate > "2026-01-01") {
    if (isBlank(record.taxableYtd)) issues.push({ employee: record.employee, issue: "Renta gravable acumulada vacía" });
    if (isBlank(record.taxWithheldYtd)) issues.push({ employee: record.employee, issue: "IR retenido acumulado vacío" });
  }
  const expectedCycle = record.group === "Nomina Quincenal INSS" ? record.monthlyBase / 2 : record.monthlyBase;
  if (typeof record.cycleBase !== "number" || Math.abs(record.cycleBase - expectedCycle) > 0.005) {
    issues.push({ employee: record.employee, issue: "Base por ciclo no coincide" });
  }
}

const summary = {
  totalRows: records.length,
  excluded: {
    employee: excluded.employee,
    employeeName: excluded.employeeName,
    groupInFile: excluded.group,
    monthlyBaseInFile: excluded.monthlyBase,
    effectiveDateInFile: excluded.effectiveDate,
  },
  monthly: records.filter((r) => r.employee !== excluded.employee && r.group === "Nomina Mensual INSS").length,
  bimonthly: records.filter((r) => r.employee !== excluded.employee && r.group === "Nomina Quincenal INSS").length,
  proposedAssignments: records.filter((r) => r.employee !== excluded.employee && allowedGroups.has(r.group)).length,
  duplicateCodes: [...new Set(duplicateCodes)],
  issueCount: issues.length,
  issues,
  totals: {
    monthlyBase: records
      .filter((r) => r.employee !== excluded.employee)
      .reduce((sum, r) => sum + (typeof r.monthlyBase === "number" ? r.monthlyBase : 0), 0),
    cycleBase: records
      .filter((r) => r.employee !== excluded.employee)
      .reduce((sum, r) => sum + (typeof r.cycleBase === "number" ? r.cycleBase : 0), 0),
  },
};

console.log("SUMMARY");
console.log(JSON.stringify(summary, null, 2));
console.log("RECORDS");
console.log(JSON.stringify(records.map(({ cycleFormula, statusFormula, ...record }) => record), null, 2));

const keyRows = await workbook.inspect({
  kind: "table",
  range: "Distribución!A8:O15",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 15,
  maxChars: 12000,
});
console.log("KEY_ROWS");
console.log(keyRows.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});
console.log("FORMULA_ERRORS");
console.log(formulaErrors.ndjson);

const preview = await workbook.render({
  sheetName: "Distribución",
  range: "A1:O20",
  scale: 1.3,
  format: "png",
});
await fs.mkdir("D:/App/ProyectoERPNext/FrappeDocker/outputs/payroll-distribution-review-20260910", { recursive: true });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
console.log(`PREVIEW=${previewPath}`);
