import { FilterItem, FilterValue } from "@/contexts/FilterContext";

export const toggleFilter = (
  filters: FilterItem[],
  field: string,
  op: string,
  value: FilterValue
): FilterItem[] => {
  const exists = filters.some(
    (f) => f.field === field && f.op === op && f.value === value
  );

  if (exists) {
    return filters.filter(
      (f) => !(f.field === field && f.op === op && f.value === value)
    );
  } else {
    return [...filters, { field, op, value } as FilterItem];
  }
};

export const toggleDateFilter = (
  filters: FilterItem[],
  field: string,
  op: string,
  value: FilterValue
): FilterItem[] => {
  const sameExists = filters.some(
    (f) => f.field === field && f.op === op && f.value === value
  );

  const exists = filters.some(
    (f) => f.field === field && f.op === op
  );

  if (sameExists) {
    return filters.filter(
      (f) => !(f.field === field && f.op === op && f.value === value)
    );
  } else if (exists) {
    const newFilters = filters.filter(
      (f) => !(f.field === field && f.op === op)
    );
    return [...newFilters, { field, op, value } as FilterItem];
  } else {
    return [...filters, { field, op, value } as FilterItem];
  }
};

export const togglePriceRangeFilter = (
  filters: FilterItem[],
  field: string,
  op: string,
  value: [number, number]
): FilterItem[] => {
  const sameExists = filters.some(
    (f) => f.field === field && f.op === op && f.value === value
  );

  const exists = filters.some(
    (f) => f.field === field && f.op === op
  );

  if (sameExists) {
    return filters.filter(
      (f) => !(f.field === field && f.op === op && f.value === value)
    );
  } else if (exists) {
    const newFilters = filters.filter(
      (f) => !(f.field === field && f.op === op)
    );
    return [...newFilters, { field, op, value } as FilterItem];
  } else {
    return [...filters, { field, op, value } as FilterItem];
  }
};
