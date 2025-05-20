'use client';
import React, { createContext, useContext, useState } from 'react';

export type FilterTuple = [string, string, string];

interface FilterContextType {
    filters: FilterTuple[];
    setFilters: React.Dispatch<React.SetStateAction<FilterTuple[]>>;
    orderBy: string;
    setOrderBy: React.Dispatch<React.SetStateAction<string>>;
    filterCount: Record<string, number>;
    setFilterCount: React.Dispatch<React.SetStateAction<Record<string, number>>>;
    selectedOptions: Record<string, Set<any>>;
    setSelectedOptions: React.Dispatch<React.SetStateAction<Record<string, Set<any>>>>;
    filterOptions: string[];
    orderByOptions: Record<string, string>;
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

type FilterProviderProps = {
    children: React.ReactNode;
    filterOptions: string[];
    orderByOptions: Record<string, string>;
};

export const FilterProvider: React.FC<FilterProviderProps> = ({ children, filterOptions, orderByOptions }) => {
    const [filters, setFilters] = useState<FilterTuple[]>([]);
    const [orderBy, setOrderBy] = useState<string>("");
    const [filterCount, setFilterCount] = useState<Record<string, number>>(
        filterOptions.map((filter) => [filter, 0]).reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {})
    );

    const [selectedOptions, setSelectedOptions] = useState<Record<string, Set<any>>>({});

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
