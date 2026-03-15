'use client';
import React from 'react';
import styled from 'styled-components';
import Container from '@/components/Container/Container';
import DetailedMainTitle from '@/components/DetailedMainTitle/DetailedMainTitle';
import ReturnPage from '@/components/ReturnPage/ReturnPage';
import InfoCard from '@/components/InfoCard/InfoCard';
import formatAmount from '@/utils/amountFormat';
import getCurrencySymbol from '@/utils/getCurrencySymbol';
import SearchBar from '@/components/SearchBar/SearchBar';
import { FilterProvider } from '@/contexts/FilterContext';
import {
    AuctionDetailFilterOptions,
    AuctionDetailOrderByOptions
} from './auction_detail.utils';
import DataTable from '@/components/DataTable/DataTable';
import { LotColumns, LotType } from '@/types/lotApi';

const InfoCardContainer = styled.div`
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    margin: 20px 0;
`;

type AuctionDetailClientProps = {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    data: any;
};

const AuctionDetailContent = ({ data }: AuctionDetailClientProps) => {
    return (
        <Container>
            <ReturnPage text="Auctions"/>
            <DetailedMainTitle 
                title={data.auction_title}
                auction_house={data.auction_house}
                region={data.city}
                country={data.continent}
                start_date={data.start_date}
                end_date={data.end_date}
                auction_type={data.auction_type}
            />
            <InfoCardContainer onClick={() => {console.log(data);}}>
                <InfoCard
                    title="Total Lots"
                    description="The number of lots / sold in the auction."
                    info={data.sales?.lots || 0}
                    infoDescription={`${data.sales?.sold || 0} lots sold (${data.sales?.sold && data.sales?.lots ? (data.sales.sold / data.sales.lots * 100).toFixed(2) : 0}%)`}
                />
                <InfoCard
                    title="Total Sales"
                    description="Total Realized"
                    info={`${getCurrencySymbol(data.sales?.currency)}${formatAmount(data.sales?.total_sales || 0)}`}
                    infoDescription={`Est: ${getCurrencySymbol(data.sales?.currency)}${formatAmount(data.sales?.total_low_estimate || 0)} - ${getCurrencySymbol(data.sales?.currency)}${formatAmount(data.sales?.total_high_estimate || 0)}`}
                />
                <InfoCard
                    title="Volume Sold"
                    description="Total volume in Milli-liters"
                    info={`${formatAmount(data.sales?.volume_sold || 0)} ML`}
                    infoDescription="This is the auction ID."
                />
                <InfoCard
                    title="Top Lot"
                    description="Lot with highest realized price"
                    info={`${data.sales?.top_lot || '-'}`}
                    infoDescription={`ID: ${data.sales?.top_lot || '-'}`}
                />
            </InfoCardContainer>
            <SearchBar type="lots" />
            <DataTable<LotType> columns={LotColumns} data={data.lots || []} />
        </Container>
    );
};

export default function AuctionDetailClient({ data }: AuctionDetailClientProps) {
    return (
        <FilterProvider filterOptions={AuctionDetailFilterOptions} orderByOptions={AuctionDetailOrderByOptions}>
            <AuctionDetailContent data={data} />
        </FilterProvider>
    );
}
