import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const helper_source = readFileSync(
	new URL(
		"../../images/custom/framework_overlays/frappe/frappe/public/js/frappe/ui/toolbar/bilingual_fuzzy_search.js",
		import.meta.url,
	),
	"utf8",
);
const helper_module = await import(
	`data:text/javascript;base64,${Buffer.from(helper_source).toString("base64")}`
);
const { bilingual_fuzzy_search } = helper_module;

const translations = {
	"Sales Invoice": "Factura de venta",
	"Purchase Order Analysis": "Análisis de orden de compra",
};

function localize(value) {
	return translations[value] || value;
}

function contains_match(keywords, item, return_matches) {
	const query = keywords.toLocaleLowerCase();
	const candidate = item.toLocaleLowerCase();
	const start = candidate.indexOf(query);
	if (start < 0) return [false, 0, []];
	const matches = return_matches
		? Array.from({ length: query.length }, (_, offset) => start + offset)
		: [];
	return [true, 100 - start, matches];
}

test("matches the Spanish label and highlights the localized text", () => {
	const result = bilingual_fuzzy_search(
		"factura",
		"Sales Invoice",
		true,
		localize,
		contains_match,
	);
	assert.equal(result.score, 100);
	assert.equal(result.marked_string, "<mark>Factura</mark> de venta");
});

test("matches the canonical English name but presents the Spanish label", () => {
	const result = bilingual_fuzzy_search(
		"sales invoice",
		"Sales Invoice",
		true,
		localize,
		contains_match,
	);
	assert.equal(result.score, 100);
	assert.equal(result.marked_string, "Factura de venta");
});

test("returns the best score from either alias without changing the canonical input", () => {
	const canonical = "Purchase Order Analysis";
	const score = bilingual_fuzzy_search(
		"purchase order",
		canonical,
		false,
		localize,
		contains_match,
	);
	assert.equal(score, 100);
	assert.equal(canonical, "Purchase Order Analysis");
});

test("keeps English behavior when no translation exists", () => {
	const result = bilingual_fuzzy_search("user", "User", true, localize, contains_match);
	assert.equal(result.marked_string, "<mark>User</mark>");
});
