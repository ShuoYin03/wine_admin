'use client';
import React, { createContext, useContext, useState } from 'react';
import { keyMap } from '@/utils/staticData';

export type FilterValue = string | number | boolean | number[];

export type FilterOperator = '=' | '~' | '>' | '<' | '>=' | '<=' | '><' | '@>';

export type FilterItem = {
    field: string;
    op: FilterOperator;
    value: FilterValue;
};

const reverseKeyMap: Record<string, string> = Object.fromEntries(
    Object.entries(keyMap).map(([label, field]) => [field, label])
);

function deriveFilterCount(filterOptions: string[], initialFilters: FilterItem[]): Record<string, number> {
    const counts = filterOptions.reduce<Record<string, number>>((acc, f) => ({ ...acc, [f]: 0 }), {});
    for (const { field } of initialFilters) {
        const label = reverseKeyMap[field];
        if (label !== undefined && label in counts) {
            counts[label] += 1;
        }
    }
    return counts;
}

function deriveSelectedOptions(initialFilters: FilterItem[]): Record<string, Set<string>> {
    const result: Record<string, Set<string>> = {};
    for (const { field, op, value } of initialFilters) {
        const label = reverseKeyMap[field];
        if (!label || op === '><' || op === '<=' || op === '>=') continue;
        if (!result[label]) result[label] = new Set<string>();
        result[label].add(String(value));
    }
    return result;
}

interface FilterContextType {
    filters: FilterItem[];
    setFilters: React.Dispatch<React.SetStateAction<FilterItem[]>>;
    orderBy: string;
    setOrderBy: React.Dispatch<React.SetStateAction<string>>;
    filterCount: Record<string, number>;
    setFilterCount: React.Dispatch<React.SetStateAction<Record<string, number>>>;
    selectedOptions: Record<string, Set<string>>;
    setSelectedOptions: React.Dispatch<React.SetStateAction<Record<string, Set<string>>>>;
    filterOptions: string[];
    orderByOptions: Record<string, string>;
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

type FilterProviderProps = {
    children: React.ReactNode;
    filterOptions: string[];
    orderByOptions: Record<string, string>;
    initialFilters?: FilterItem[];
    initialOrderBy?: string;
};

export const FilterProvider: React.FC<FilterProviderProps> = ({ children, filterOptions, orderByOptions, initialFilters = [], initialOrderBy = "" }) => {
    const [filters, setFilters] = useState<FilterItem[]>(initialFilters);
    const [orderBy, setOrderBy] = useState<string>(initialOrderBy);
    const [filterCount, setFilterCount] = useState<Record<string, number>>(
        () => deriveFilterCount(filterOptions, initialFilters)
    );
    const [selectedOptions, setSelectedOptions] = useState<Record<string, Set<string>>>(
        () => deriveSelectedOptions(initialFilters)
    );

    return (
        <FilterContext.Provider
            value={{
                filters,
                setFilters,
                orderBy,
                setOrderBy,
                filterCount,
                setFilterCount,
                selectedOptions,
                setSelectedOptions,
                filterOptions,
                orderByOptions
            }}
        >
            {children}
        </FilterContext.Provider>
    );
};

export const useFilterContext = (): FilterContextType => {
    const context = useContext(FilterContext);
    if (!context) {
        throw new Error('useFilterContext must be used within a FilterProvider');
    }
    return context;
};
