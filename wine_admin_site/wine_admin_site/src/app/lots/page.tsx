'use client';
import React, { useState, useEffect} from 'react';
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

const LotContent = () => {
    const { filters, orderBy } = useFilterContext();
    const { data, setData } = useLotDataContext();
    const [page, setPage] = useState<number>(1);
    const [page_size, setPageSize] = useState<number>(10);
    const [count, setCount] = useState<number>(0);

    useEffect(() => {
        const fetchData = async () => {
            const payload = {
                filters: filters,
                order_by: orderBy,
                page: page,
                page_size: page_size, 
                return_count: true,
            };

            const response = await fetch('/api/lot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            
            const data = await response.json();
            const { result, count } = data;
            setData(result);
            setCount(count);
        };
        fetchData();
    }, [filters, orderBy, page, page_size]);

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
        if (direction && page < Math.ceil(count / page_size)) {
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
        <DataTableBottom page={page} setPage={setPage} pageSize={page_size} setPageSize={setPageSize} handlePageChange={handlePageChange} handlePageSizeChange={handlePageSizeChange} count={count}/>
      </Container>
    );
}

const Lots = () => {
    return (
        <LotDataProvider>
            <FilterProvider filterOptions={LotFilterOptions} orderByOptions={LotOrderByOptions} >
                <LotContent />
            </FilterProvider>
        </LotDataProvider>
    );
}

export default Lots;