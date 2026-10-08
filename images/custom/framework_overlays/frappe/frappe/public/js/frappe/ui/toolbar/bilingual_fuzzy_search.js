function mark_matches(item, matches) {
	const match_array = Array(item.length).fill(0);
	matches.forEach((index) => (match_array[index] = 1));

	let marked_string = "";
	let buffer = "";
	const flush_buffer = () => {
		if (!buffer) return "";
		const marked = `<mark>${buffer}</mark>`;
		buffer = "";
		return marked;
	};

	match_array.forEach((is_match, index) => {
		if (is_match) {
			buffer += item[index];
		} else {
			marked_string += flush_buffer();
			marked_string += item[index];
		}
	});
	return marked_string + flush_buffer();
}

/**
 * Match both the canonical and localized names while always presenting the
 * localized name. Callers continue to own canonical routes and identifiers.
 */
export function bilingual_fuzzy_search(
	keywords = "",
	canonical_item = "",
	return_marked_string = false,
	localize,
	fuzzy_match,
) {
	const canonical = canonical_item || "";
	const localized = localize(canonical) || canonical;
	const [, localized_score, localized_matches] = fuzzy_match(
		keywords,
		localized,
		return_marked_string,
	);

	let canonical_score = localized_score;
	if (canonical !== localized) {
		[, canonical_score] = fuzzy_match(keywords, canonical, false);
	}

	const score = Math.max(localized_score, canonical_score);
	if (!return_marked_string) return score;
	if (!score || canonical_score > localized_score) {
		return { score, marked_string: localized };
	}

	return {
		score,
		marked_string: mark_matches(localized, localized_matches),
	};
}
