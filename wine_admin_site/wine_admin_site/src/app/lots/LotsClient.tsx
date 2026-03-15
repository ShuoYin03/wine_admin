'use client';
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar from '@/components/SearchBar/SearchBar';
import DataTable from '@/components/DataTable/DataTable';
import { LotDisplayType } from '@/types/lotApi';
import MainTitle from '@/components/MainTitle/MainTitle';
import { LotColumns } from '@/types/lotApi';
import DataTableBottom from '@/components/DataTable/DataTableBottom';
import Container from '@/components/Container/Container';
import { 
    FilterProvider,
    useFilterContext
} from '@/contexts/FilterContext';
import { 
    LotFilterOptions,
    LotOrderByOptions
} from './lot.utils';
import {
    LotDataProvider,
    useLotDataContext
} from '@/contexts/lotCreateDataContext';

type LotsClientProps = {
    initialData: LotDisplayType[];
    initialCount: number;
    initialPage: number;
    initialPageSize: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    initialFilters: any[];
    initialOrderBy: string;
};

const LotContent = ({ initialCount, initialPage, initialPageSize }: LotsClientProps) => {
    const { filters, orderBy } = useFilterContext();
    const { data } = useLotDataContext();
    const router = useRouter();
    const [, startTransition] = React.useTransition();
    
    const [page, setPage] = useState<number>(initialPage);
    const [page_size, setPageSize] = useState<number>(initialPageSize);

    // Sync state changes to URL for Server Component data fetching
    useEffect(() => {
        const payload = {
            filters: JSON.stringify(filters),
            orderBy: orderBy,
            page: page.toString(),
            pageSize: page_size.toString(),
        };
        const params = new URLSearchParams();
        if (filters.length > 0) params.set('filters', payload.filters);
        if (orderBy) params.set('orderBy', payload.orderBy);
        if (page > 1) params.set('page', payload.page);
        if (page_size !== 10) params.set('pageSize', payload.pageSize);
        
        startTransition(() => {
            router.replace(`/lots?${params.toString()}`, { scroll: false });
        });
    }, [filters, orderBy, page, page_size, router]);

    const handleExport = async () => {
        const payload = {
            filters: filters,
            order_by: "id"
          };
        
          const response = await fetch('http://localhost:5000/lot_export_csv', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
          });
        
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
        
          const link = document.createElement('a');
          link.href = url;
          link.download = 'lots_export.csv';
          document.body.appendChild(link);
          link.click();
          link.remove();
          window.URL.revokeObjectURL(url);
    };

    const handlePageChange = (direction: boolean) => {
        if (direction && page < Math.ceil(initialCount / page_size)) {
            setPage(page + 1);
        } else if (!direction && page > 1) {
            setPage(page - 1);
        }
    }

    const handlePageSizeChange = (size: number) => {
        setPageSize(size);
        setPage(1);
    }

    return (
      <Container>
        <MainTitle title={"Lots"} subtitle={"Browse, Search, and Manage Wine Lots"}></MainTitle>
        <SearchBar exportCallback={handleExport} type='lot'/>
        <DataTable<LotDisplayType> columns={LotColumns} data={data} />
        <DataTableBottom 
            page={page} 
            setPage={setPage} 
            pageSize={page_size} 
            setPageSize={setPageSize} 
            handlePageChange={handlePageChange} 
            handlePageSizeChange={handlePageSizeChange} 
            count={initialCount}
        />
      </Container>
    );
};

export default function LotsClient(props: LotsClientProps) {
    return (
        <LotDataProvider initialData={props.initialData}>
            <FilterProvider 
                filterOptions={LotFilterOptions} 
                orderByOptions={LotOrderByOptions}
                initialFilters={props.initialFilters}
                initialOrderBy={props.initialOrderBy}
            >
                <LotContent {...props} />
            </FilterProvider>
        </LotDataProvider>
    );
}
