function sortSchoolGrades(grades, nameKey) {
  const key = nameKey || "grade_form";
  const list = Array.isArray(grades) ? grades.slice() : [];

  function parse(name) {
    const raw = String(name || "")
      .trim()
      .toUpperCase()
      .replace(/\s+/g, " ");
    if (["PLAY GROUP", "PLAYGROUP", "PLAY-GROUP"].includes(raw)) {
      return [0, 0, raw];
    }
    if (raw === "IGCSE") {
      return [4, 999, raw];
    }

    const compact = raw.replace(/ /g, "");
    let match = compact.match(/^PP([12])/);
    if (match) return [1, Number(match[1]), raw];

    match = compact.match(/^GRADE([1-9]|1[0-2])/);
    if (match) return [2, Number(match[1]), raw];

    match = compact.match(/^FORM([1-4])/);
    if (match) return [3, Number(match[1]), raw];

    return [999, 999, raw];
  }

  return list.sort((left, right) => {
    const leftName = typeof left === "string" ? left : left[key];
    const rightName = typeof right === "string" ? right : right[key];
    const a = parse(leftName);
    const b = parse(rightName);
    if (a[0] !== b[0]) return a[0] - b[0];
    if (a[1] !== b[1]) return a[1] - b[1];
    return String(a[2]).localeCompare(String(b[2]), undefined, {
      numeric: true,
    });
  });
}
