'use client';
import React, { useState, useEffect} from 'react';
import styled from 'styled-components';
import SearchBar from '@/components/SearchBar/SearchBar';
import DataTable from '@/components/DataTable/DataTable';
import { LotDisplayType } from '@/types/lotApi';
import MainTitle from '@/components/MainTitle/MainTitle';
import { LotColumns } from '@/types/lotApi';
import DataTableBottom from '@/components/DataTable/DataTableBottom';

const HomeContainer = styled.div`
    display: flex;
    flex-direction: column;
    background-color: #FDF8F5;
    padding: 0px 200px;
    padding-bottom: 90px;
    min-height: 82vh;
`;

const fakeData: LotDisplayType[] = [
    {
        id: 3,
        wine_name: "Wine C",
        vintage: 2020,
        unit: 3,
        end_price: 75,
        sold: true,
    }
]

const Home = () => {
    const [filters, setFilters] = useState<object>({});
    const [order_by, setOrderBy] = useState<string>("");
    const [page, setPage] = useState<number>(1);
    const [page_size, setPageSize] = useState<number>(10);
    const [data, setData] = useState<LotDisplayType[]>([]);
    const [count, setCount] = useState<number>(0);

    useEffect(() => {
        const fetchData = async () => {
            const payload = {
                filters: filters,
                order_by: order_by,
                page: page,
                page_size: page_size, 
                return_count: true,
            };

            const response = await fetch('/api/lot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            
            const data = await response.json();
            const { result, count } = data;
            setData(result);
            setCount(count);
        };
        fetchData();
    }, [filters, order_by, page, page_size]);

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

    const handleFilterChange = (filters: object) => {
        setFilters(filters);
        setPage(1);
    }
    
    const handleOrderByChange = (orderBy: string) => {
        setOrderBy(orderBy);
        setPage(1);
    }

    return (
      <HomeContainer>
        <MainTitle title={"Wine Admin Site"} subtitle={"Browse, Search, and Manage Wine Lots"}></MainTitle>
        <SearchBar callbackFilter={handleFilterChange} callbackOrderBy={handleOrderByChange}/>
        <DataTable<LotDisplayType> columns={LotColumns} data={data} />
        <DataTableBottom page={page} setPage={setPage} pageSize={page_size} setPageSize={setPageSize} handlePageChange={handlePageChange} handlePageSizeChange={handlePageSizeChange} count={count}/>
      </HomeContainer>
    );
}

export default Home;