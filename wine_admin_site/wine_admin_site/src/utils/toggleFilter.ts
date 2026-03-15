import { FilterTuple, FilterValue } from "@/contexts/FilterContext";

export const toggleFilter = (
  filters: FilterTuple[],
  column: string,
  operator: string,
  value: FilterValue
): FilterTuple[] => {
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
  filters: FilterTuple[],
  column: string,
  operator: string,
  value: FilterValue
): FilterTuple[] => {
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
      ([col, op]) => !(col === column && op === operator)
    );
    return [...newFilters, [column, operator, value]];
  } else {
    return [...filters, [column, operator, value]];
  }
};

export const togglePriceRangeFilter = (
  filters: FilterTuple[],
  column: string,
  operator: string,
  value: [number, number]
): FilterTuple[] => {
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
      ([col, op]) => !(col === column && op === operator)
    );
    return [...newFilters, [column, operator, value]];
  } else {
    return [...filters, [column, operator, value]];
  }
};
