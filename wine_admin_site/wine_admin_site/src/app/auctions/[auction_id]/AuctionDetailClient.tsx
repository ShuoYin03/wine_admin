'use client';
import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import styled from 'styled-components';
import Container from '@/components/Container/Container';
import DetailedMainTitle from '@/components/DetailedMainTitle/DetailedMainTitle';
import ReturnPage from '@/components/ReturnPage/ReturnPage';
import InfoCard from '@/components/InfoCard/InfoCard';
import formatAmount from '@/utils/amountFormat';
import getCurrencySymbol from '@/utils/getCurrencySymbol';
import SearchBar from '@/components/SearchBar/SearchBar';
import { FilterProvider, useFilterContext } from '@/contexts/FilterContext';
import {
    AuctionDetailFilterOptions,
    AuctionDetailOrderByOptions
} from './auction_detail.utils';
import DataTable from '@/components/DataTable/DataTable';
import DataTableBottom from '@/components/DataTable/DataTableBottom';
import { LotColumns, LotDisplayType } from '@/types/lotApi';
import { LotDataProvider, useLotDataContext } from '@/contexts/lotCreateDataContext';

const InfoCardContainer = styled.div`
    display: flex;
    align-items: stretch;
    justify-content: space-between;
    gap: 20px;
    margin: 20px 0;
`;

type AuctionDetailClientProps = {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    auctionData: any;
    initialLots: LotDisplayType[];
    initialCount: number;
    initialPage: number;
    initialPageSize: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    initialFilters: any[];
    initialOrderBy: string;
};

const AuctionDetailContent = ({ auctionData, initialCount, initialPage, initialPageSize }: AuctionDetailClientProps) => {
    const { filters, orderBy } = useFilterContext();
    const { data } = useLotDataContext();
    const router = useRouter();
    const params = useParams();
    const auction_id = params.auction_id as string;
    const [, startTransition] = React.useTransition();

    const [page, setPage] = useState<number>(initialPage);
    const [page_size, setPageSize] = useState<number>(initialPageSize);

    useEffect(() => {
        const urlParams = new URLSearchParams();
        if (filters.length > 0) urlParams.set('filters', JSON.stringify(filters));
        if (orderBy) urlParams.set('orderBy', orderBy);
        if (page > 1) urlParams.set('page', page.toString());
        if (page_size !== 30) urlParams.set('pageSize', page_size.toString());

        startTransition(() => {
            router.replace(`/auctions/${auction_id}?${urlParams.toString()}`, { scroll: false });
        });
    }, [filters, orderBy, page, page_size, router, auction_id]);

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
        <Container>
            <ReturnPage text="Auctions"/>
            <DetailedMainTitle 
                title={auctionData.auction_title}
                auction_house={auctionData.auction_house}
                region={auctionData.city}
                country={auctionData.continent}
                start_date={auctionData.start_date}
                end_date={auctionData.end_date}
                auction_type={auctionData.auction_type}
            />
            <InfoCardContainer onClick={() => {console.log(auctionData);}}>
                <InfoCard
                    title="Total Lots"
                    description="The number of lots / sold in the auction."
                    info={auctionData.sales?.lots || 0}
                    infoDescription={`${auctionData.sales?.sold || 0} lots sold (${auctionData.sales?.sold && auctionData.sales?.lots ? (auctionData.sales.sold / auctionData.sales.lots * 100).toFixed(2) : 0}%)`}
                />
                <InfoCard
                    title="Total Sales"
                    description="Total Realized"
                    info={`${getCurrencySymbol(auctionData.sales?.currency)}${formatAmount(auctionData.sales?.total_sales || 0)}`}
                    infoDescription={`Est: ${getCurrencySymbol(auctionData.sales?.currency)}${formatAmount(auctionData.sales?.total_low_estimate || 0)} - ${getCurrencySymbol(auctionData.sales?.currency)}${formatAmount(auctionData.sales?.total_high_estimate || 0)}`}
                />
                <InfoCard
                    title="Volume Sold"
                    description="Total volume in Milli-liters"
                    info={`${formatAmount(auctionData.sales?.volume_sold || 0)} ML`}
                    infoDescription="This is the auction ID."
                />
                <InfoCard
                    title="Top Lot"
                    description="Lot with highest realized price"
                    info={`${auctionData.sales?.top_lot || '-'}`}
                    infoDescription={`ID: ${auctionData.sales?.top_lot || '-'}`}
                    copyValue={auctionData.sales?.top_lot ?? undefined}
                />
            </InfoCardContainer>
            <SearchBar type="lot" />
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

export default function AuctionDetailClient(props: AuctionDetailClientProps) {
    return (
        <LotDataProvider initialData={props.initialLots}>
            <FilterProvider
                filterOptions={AuctionDetailFilterOptions}
                orderByOptions={AuctionDetailOrderByOptions}
                initialFilters={props.initialFilters}
                initialOrderBy={props.initialOrderBy}
            >
                <AuctionDetailContent {...props} />
            </FilterProvider>
        </LotDataProvider>
    );
}
