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
import { AuctionType } from '@/types/auctionApi';

type AuctionsClientProps = {
    initialData: AuctionType[];
    initialCount: number;
    initialPage: number;
    initialPageSize: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    initialFilters: any[];
    initialOrderBy: string;
};

const AuctionContent = ({ initialCount, initialPage, initialPageSize }: AuctionsClientProps) => {
    const { filters, orderBy } = useFilterContext();
    const { data } = useAuctionDataContext();
    const router = useRouter();
    const [, startTransition] = React.useTransition();
    
    const [page, setPage] = useState<number>(initialPage);
    const [page_size, setPageSize] = useState<number>(initialPageSize);

    // Reset to page 1 if filters or ordering change
    useEffect(() => {
        setPage(1);
    }, [filters, orderBy]);

    // Sync state changes to URL for Server Component data fetching
    useEffect(() => {
        const payload = {
            filters: JSON.stringify(filters),
            orderBy: orderBy,
            page: page.toString(),
            pageSize: page_size.toString(),
        };
        const params = new URLSearchParams();
        if (filters.length > 0) params.set('filters', payload.filters);
        if (orderBy) params.set('orderBy', payload.orderBy);
        if (page > 1) params.set('page', payload.page);
        if (page_size !== 12) params.set('pageSize', payload.pageSize);
        
        startTransition(() => {
            router.replace(`/auctions?${params.toString()}`, { scroll: false });
        });
    }, [filters, orderBy, page, page_size, router]);

    const handlePageChange = (direction: boolean) => {
        if (direction && page < Math.ceil(initialCount / page_size)) {
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
                count={initialCount}/>
        </Container>
    );
};

export default function AuctionsClient(props: AuctionsClientProps) {
    return (
        <AuctionDataProvider initialData={props.initialData}>
            <FilterProvider 
                filterOptions={AuctionFilterOptions} 
                orderByOptions={AuctionOrderByOptions}
                initialFilters={props.initialFilters}
                initialOrderBy={props.initialOrderBy}
            >
                <AuctionContent {...props} />
            </FilterProvider>
        </AuctionDataProvider>
    );
}
