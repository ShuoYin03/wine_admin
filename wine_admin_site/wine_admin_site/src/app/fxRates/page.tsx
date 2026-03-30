import React from 'react';
import FxRatesClient from './FxRatesClient';
import { RatesDisplayType } from '@/types/ratesApi';
import { FilterItem } from '@/contexts/FilterContext';

export const metadata = {
    title: 'FX Rates - Wine Admin Site',
};

export default async function FxRatesPage(props: {
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    const searchParams = await props.searchParams;

    let rawFilters: FilterItem[] = [];
    if (searchParams.filters) {
        try {
            rawFilters = JSON.parse(searchParams.filters as string);
        } catch (e) {
            console.error('Failed to parse filters', e);
        }
    }

    const orderBy = (searchParams.orderBy as string) || '';
    const page = parseInt((searchParams.page as string) || '1', 10);
    const pageSize = parseInt((searchParams.pageSize as string) || '20', 10);

    const payload = {
        filters: rawFilters,
        order_by: orderBy,
        page,
        page_size: pageSize,
        return_count: true,
    };

    let data: RatesDisplayType[] = [];
    let count = 0;

    try {
        const response = await fetch(`${process.env.PYTHON_API_URL}/rates_query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            cache: 'no-store',
        });
        if (response.ok) {
            const raw = await response.json();
            data = raw.data ?? [];
            count = raw.meta?.count ?? 0;
        }
    } catch (e) {
        console.error('Failed to fetch fx rates', e);
    }

    return (
        <FxRatesClient
            initialData={data}
            initialCount={count}
            initialPage={page}
            initialPageSize={pageSize}
            initialFilters={rawFilters}
            initialOrderBy={orderBy}
        />
    );
}