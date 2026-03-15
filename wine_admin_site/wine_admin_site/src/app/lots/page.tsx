import React from 'react';
import LotsClient from './LotsClient';
import { filterData } from '../api/lot/lot.utils';

export const metadata = {
  title: 'Lots - Wine Admin Site'
};

export default async function LotsPage(props: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
    const searchParams = await props.searchParams;
    let rawFilters = [];
    if (searchParams.filters) {
        try {
            rawFilters = JSON.parse(searchParams.filters as string);
        } catch (e) {
            console.error("Failed to parse filters", e);
        }
    }
    
    const orderBy = (searchParams.orderBy as string) || '';
    const page = parseInt((searchParams.page as string) || '1', 10);
    const pageSize = parseInt((searchParams.pageSize as string) || '10', 10);

    const payload = {
        filters: rawFilters,
        order_by: orderBy,
        page: page,
        page_size: pageSize,
        return_count: true
    };

    let data: import('@/types/lotApi').LotDisplayType[] = [];
    let count = 0;

    try {
        const response = await fetch(`http://localhost:5000/lot_query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            cache: 'no-store'
        });
        
        if (response.ok) {
            const rawData = await response.json();
            data = filterData(rawData.lots);
            count = rawData.count;
        }
    } catch (e) {
        console.error("Failed to fetch lots", e);
    }

    return (
        <LotsClient 
            initialData={data} 
            initialCount={count}
            initialPage={page}
            initialPageSize={pageSize}
            initialFilters={rawFilters}
            initialOrderBy={orderBy}
        />
    );
}
