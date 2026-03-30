'use client';
import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useRouter } from 'next/navigation';
import MainTitle from '@/components/MainTitle/MainTitle';
import DataTable from '@/components/DataTable/DataTable';
import DataTableBottom from '@/components/DataTable/DataTableBottom';
import SearchBar from '@/components/SearchBar/SearchBar';
import { RatesDisplayType, RatesColumns } from '@/types/ratesApi';
import { FilterProvider, useFilterContext, FilterItem } from '@/contexts/FilterContext';
import { FxRatesFilterOptions, FxRatesOrderByOptions } from './fxRates.utils';

const FxRatesContainer = styled.div`
    display: flex;
    flex-direction: column;
    background-color: #FDF8F5;
    padding: 0px 200px;
    padding-bottom: 90px;
    min-height: 82vh;
`;

type FxRatesClientProps = {
    initialData: RatesDisplayType[];
    initialCount: number;
    initialPage: number;
    initialPageSize: number;
    initialFilters: FilterItem[];
    initialOrderBy: string;
};

const FxRatesContent = ({
    initialData,
    initialCount,
    initialPage,
    initialPageSize,
}: FxRatesClientProps) => {
    const { filters, orderBy } = useFilterContext();
    const router = useRouter();
    const [, startTransition] = React.useTransition();

    const [page, setPage] = useState<number>(initialPage);
    const [page_size, setPageSize] = useState<number>(initialPageSize);

    useEffect(() => {
        const params = new URLSearchParams();
        if (filters.length > 0) params.set('filters', JSON.stringify(filters));
        if (orderBy) params.set('orderBy', orderBy);
        if (page > 1) params.set('page', page.toString());
        if (page_size !== 20) params.set('pageSize', page_size.toString());

        startTransition(() => {
            router.replace(`/fxRates?${params.toString()}`, { scroll: false });
        });
    }, [filters, orderBy, page, page_size, router]);

    const handlePageChange = (direction: boolean) => {
        if (direction && page < Math.ceil(initialCount / page_size)) {
            setPage(page + 1);
        } else if (!direction && page > 1) {
            setPage(page - 1);
        }
    };

    const handlePageSizeChange = (size: number) => {
        setPageSize(size);
        setPage(1);
    };

    return (
        <FxRatesContainer>
            <MainTitle title="FX Rates" subtitle="Browse and Filter FX Exchange Rates" />
            <SearchBar type="fxRates" />
            <DataTable<RatesDisplayType> columns={RatesColumns} data={initialData} />
            <DataTableBottom
                page={page}
                setPage={setPage}
                pageSize={page_size}
                setPageSize={setPageSize}
                handlePageChange={handlePageChange}
                handlePageSizeChange={handlePageSizeChange}
                count={initialCount}
            />
        </FxRatesContainer>
    );
};

export default function FxRatesClient(props: FxRatesClientProps) {
    return (
        <FilterProvider
            filterOptions={FxRatesFilterOptions}
            orderByOptions={FxRatesOrderByOptions}
            initialFilters={props.initialFilters}
            initialOrderBy={props.initialOrderBy}
        >
            <FxRatesContent {...props} />
        </FilterProvider>
    );
}
