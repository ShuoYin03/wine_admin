type FilterTriple = [string, string, any];

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

export const toggleDateFilter = (
  filters: FilterTriple[],
  column: string,
  operator: string,
  value: any
): FilterTriple[] => {
  const sameExists = filters.some(
    ([col, op, val]) => col === column && op === operator && val === value
  );

  const exists = filters.some(
    ([col, op]) => col === column && op === operator
  );

  if (sameExists) {
    return filters.filter(
      ([col, op, val]) => !(col === column && op === operator && val === value)
    );
  } else if (exists){
    const newFilters = filters.filter(
      ([col, op, _]) => !(col === column && op === operator)
    );
    return [...newFilters, [column, operator, value]];
  } else {
    return [...filters, [column, operator, value]];
  }
};

export const togglePriceRangeFilter = (
  filters: FilterTriple[],
  column: string,
  operator: string,
  value: [number, number]
): FilterTriple[] => {
  const sameExists = filters.some(
    ([col, op, val]) => col === column && op === operator && val === value
  );

  const exists = filters.some(
    ([col, op]) => col === column && op === operator
  );

  if (sameExists) {
    return filters.filter(
      ([col, op, val]) => !(col === column && op === operator && val === value)
    );
  } else if (exists){
    const newFilters = filters.filter(
      ([col, op, _]) => !(col === column && op === operator)
    );
    return [...newFilters, [column, operator, value]];
  } else {
    return [...filters, [column, operator, value]];
  }
};