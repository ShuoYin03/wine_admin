'use client';
import React, { useState, useEffect } from 'react';
import SearchBar from '@/components/SearchBar/SearchBar';
import MainTitle from '@/components/MainTitle/MainTitle';
import DataTableBottom from '@/components/DataTable/DataTableBottom';
import { 
    AuctionFilterOptions,
    AuctionOrderByOptions
 } from './auction.util';
import Container from '@/components/Container/Container';
import AuctionCard from '@/components/AuctionCard/AuctionCard';
import CardGrid from '@/components/CardGrid/CardGrid';
import { useRouter } from 'next/navigation';
import { 
    FilterProvider,
    useFilterContext
} from '@/contexts/FilterContext';
import {
    AuctionDataProvider,
    useAuctionDataContext
} from '../../contexts/auctionCreateDataContext';

const AuctionContent = () => {
    const { filters, orderBy } = useFilterContext();
    const { data, setData } = useAuctionDataContext();
    const [page, setPage] = useState<number>(1);
    const [page_size, setPageSize] = useState<number>(12);
    const [count, setCount] = useState<number>(0);
    const router = useRouter();

    useEffect(() => {
        const fetchData = async () => {
            const payload = {
                filters: filters,
                order_by: orderBy,
                page: page,
                page_size: page_size, 
                return_count: true,
            };

            const response = await fetch('/api/auction', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            
            const responseData = await response.json();
            const { result, count } = responseData;
            setData(result);
            setCount(count);
        };
        fetchData();
    }, [filters, orderBy, page, page_size]);

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

    useEffect(() => {
        setPage(1);
      }, [filters, orderBy]);
    

    return (
        <Container>
            <MainTitle title={"Auctions"} subtitle={"Browse, Search, and Manage Auctions"}></MainTitle>
            <SearchBar type="auction"/>
            <CardGrid>
                {data.map((auction, index) => (
                    <AuctionCard 
                        key={index} 
                        auction={auction} 
                        onClick={
                            () => router.push(`/auctions/${auction.external_id.replace('#', '%23')}`)
                        }
                    />
                ))}
            </CardGrid>
            <DataTableBottom 
                page={page} 
                setPage={setPage} 
                pageSize={page_size} 
                setPageSize={setPageSize} 
                handlePageChange={handlePageChange} 
                handlePageSizeChange={handlePageSizeChange} 
                count={count}/>
        </Container>
    );
}

const Auction = () => {
    return (
        <AuctionDataProvider>
            <FilterProvider filterOptions={AuctionFilterOptions} orderByOptions={AuctionOrderByOptions} >
                <AuctionContent />
            </FilterProvider>
        </AuctionDataProvider>
    );
}

export default Auction;