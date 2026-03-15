import React from 'react';
import LwinMatchingClient from './LwinMatchingClient';
import { filterData } from '../api/lwin/lwin.utils';

export const metadata = {
  title: 'Lwin Matching - Wine Admin Site'
};

export default async function LwinMatchingPage(props: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
    const searchParams = await props.searchParams;
    let rawFilters = [];
    if (searchParams.filters) {
        try {
            rawFilters = JSON.parse(searchParams.filters as string);
        } catch (e) {
            console.error("Failed to parse filters", e);
        }
    } else {
        rawFilters = [["matched", "eq", "exact_match"]];
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

    let data: import('@/types/lwinApi').LwinDisplayType[] = [];
    let count = 0;
    let counts = {
        exactCount: 0,
        multiCount: 0,
        notCount: 0
    };

    try {
        const [dataResponse, countResponse] = await Promise.all([
            fetch(`http://localhost:5000/lwin_query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                cache: 'no-store'
            }),
            fetch(`http://localhost:5000/lwin_count`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                cache: 'no-store'
            })
        ]);
        
        if (dataResponse.ok) {
            const rawData = await dataResponse.json();
            const lwins = rawData.data || [];
            data = filterData(lwins);
            count = rawData.count || 0;
        }

        if (countResponse.ok) {
            const rawCount = await countResponse.json();
            const countData = rawCount.result?.data || rawCount.data || rawCount;
            counts = {
                exactCount: countData.exact_match_count || 0,
                multiCount: countData.multi_match_count || 0,
                notCount: countData.not_match_count || 0
            };
        }
    } catch (e) {
        console.error("Failed to fetch lwin data", e);
    }

    return (
        <LwinMatchingClient 
            initialData={data} 
            initialCount={count}
            initialPage={page}
            initialPageSize={pageSize}
            initialFilters={rawFilters}
            initialOrderBy={orderBy}
            counts={counts}
        />
    );
}

