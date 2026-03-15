import React from 'react';
import AuctionsClient from './AuctionsClient';

export const metadata = {
  title: 'Auctions - Wine Admin Site'
};

export default async function AuctionsPage(props: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
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
    const pageSize = parseInt((searchParams.pageSize as string) || '12', 10);

    const payload = {
        filters: rawFilters,
        order_by: orderBy,
        page: page,
        page_size: pageSize,
        return_count: true
    };

    let data = [];
    let count = 0;

    try {
        const response = await fetch(`http://localhost:5000/auctions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            cache: 'no-store'
        });
        
        if (response.ok) {
            const rawData = await response.json();
            data = rawData.auctions;
            count = rawData.count;
        }
    } catch (e) {
        console.error("Failed to fetch auctions", e);
    }

    return (
        <AuctionsClient 
            initialData={data} 
            initialCount={count}
            initialPage={page}
            initialPageSize={pageSize}
            initialFilters={rawFilters}
            initialOrderBy={orderBy}
        />
    );
}
