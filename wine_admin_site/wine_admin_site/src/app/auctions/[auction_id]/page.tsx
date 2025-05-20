'use client';
import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useParams } from 'next/navigation';
import Container from '@/components/Container/Container';
import DetailedMainTitle from '@/components/DetailedMainTitle/DetailedMainTitle';
import ReturnPage from '@/components/ReturnPage/ReturnPage';
import InfoCard from '@/components/InfoCard/InfoCard';
import formatAmount from '@/utils/amountFormat';
import getCurrencySymbol from '@/utils/getCurrencySymbol';
import SearchBar from '@/components/SearchBar/SearchBar';
import { 
    FilterProvider,
    useFilterContext
} from '@/contexts/FilterContext';
import {
    AuctionDetailFilterOptions,
    AuctionDetailOrderByOptions
} from './auction_detail.utils';
import DataTable from '@/components/DataTable/DataTable';
import { LotColumns, LotDisplayType, LotType } from '@/types/lotApi';

const InfoCardContainer = styled.div`
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    margin: 20px 0;
`;

const AuctionDetailContent = () => {
    const { auction_id } = useParams();
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            const response = await fetch(`/api/auction?auction_id=${auction_id}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            const responseData = await response.json();
            setData(responseData.result.auction);
            setLoading(false);
        };
        fetchData();
    }, [auction_id]);

    if (loading || !data) return <Container>Loading...</Container>;

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
                    info={data.sales.lots}
                    infoDescription={`${data.sales.sold} lots sold (${data.sales.lots / data.sales.sold * 100}%)`}
                />
                <InfoCard
                    title="Total Sales"
                    description="Total Realized"
                    info={`${getCurrencySymbol(data.sales.currency)}${formatAmount(data.sales.total_sales)}`}
                    infoDescription={`Est: ${getCurrencySymbol(data.sales.currency)}${formatAmount(data.sales.total_low_estimate)} - ${getCurrencySymbol(data.sales.currency)}${formatAmount(data.sales.total_high_estimate)}`}
                />
                <InfoCard
                    title="Volume Sold"
                    description="Total volume in Milli-liters"
                    info={`${formatAmount(data.sales.volume_sold)} ML`}
                    infoDescription="This is the auction ID."
                />
                <InfoCard
                    title="Top Lot"
                    description="Lot with highest realized price"
                    info={`${data.sales.top_lot}`}
                    infoDescription={`ID: ${data.sales.top_lot}`}
                />
            </InfoCardContainer>
            <SearchBar type="lots" />
            <DataTable<LotType> columns={LotColumns} data={data.lots} />
        </Container>
    );
};

const AuctionDetailPage = () => {
    return (
        <FilterProvider filterOptions={AuctionDetailFilterOptions} orderByOptions={AuctionDetailOrderByOptions}>
            <AuctionDetailContent />
        </FilterProvider>
    );
};
export default AuctionDetailPage;