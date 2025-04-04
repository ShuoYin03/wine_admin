type FilterTriple = [string, string, string];

export const toggleFilter = (
  filters: FilterTriple[],
  column: string,
  operator: string,
  value: any
): FilterTriple[] => {
  const exists = filters.some(
    ([col, op, val]) => col === column && op === operator && val === value
  );

  if (exists) {
    return filters.filter(
      ([col, op, val]) => !(col === column && op === operator && val === value)
    );
  } else {
    return [...filters, [column, operator, value]];
  }
};
