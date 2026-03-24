import React from 'react';
import AuctionDetailClient from './AuctionDetailClient';
import Container from '@/components/Container/Container';
import { filterData } from '@/app/api/lot/lot.utils';
import { LotDisplayType } from '@/types/lotApi';

export const metadata = {
  title: 'Auction Detail - Wine Admin Site'
};

export default async function AuctionDetailPage(props: {
    params: Promise<{ auction_id: string }>;
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    const params = await props.params;
    const searchParams = await props.searchParams;
    const { auction_id } = params;

    let rawFilters: unknown[] = [];
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

    let auctionData = null;
    try {
        const response = await fetch(`http://localhost:5000/auction/${auction_id}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            cache: 'no-store',
        });

        if (response.ok) {
            const rawData = await response.json();
            auctionData = rawData.auction || rawData;
        }
    } catch (e) {
        console.error("Failed to fetch auction details", e);
    }

    let lotsData: LotDisplayType[] = [];
    let totalCount = 0;
    try {
        const lotsResponse = await fetch(`http://localhost:5000/auction/${auction_id}/lots`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filters: rawFilters,
                order_by: orderBy,
                page,
                page_size: pageSize,
                return_count: true,
            }),
            cache: 'no-store',
        });
        
        if (lotsResponse.ok) {
            const lotsRaw = await lotsResponse.json();
            lotsData = filterData(lotsRaw.lots ?? []);
            totalCount = lotsRaw.count ?? 0;
        }
    } catch (e) {
        console.error("Failed to fetch lots", e);
    }

    if (!auctionData) return <Container>Loading...</Container>;

    return (
        <AuctionDetailClient
            auctionData={auctionData}
            initialLots={lotsData}
            initialCount={totalCount}
            initialPage={page}
            initialPageSize={pageSize}
            initialFilters={rawFilters}
            initialOrderBy={orderBy}
        />
    );
}
