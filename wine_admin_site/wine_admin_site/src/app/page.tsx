'use client';
import React, { useState, useEffect} from 'react';
import styled from 'styled-components';
import { LotDisplayType } from '@/types/lotApi';
import MainTitle from '@/components/MainTitle/MainTitle';

const HomeContainer = styled.div`
    display: flex;
    flex-direction: column;
    background-color: #FDF8F5;
    padding: 0px 200px;
    padding-bottom: 90px;
    min-height: 82vh;
`;

const Home = () => {
    const [filters, setFilters] = useState<object>({});
    const [order_by, setOrderBy] = useState<string>("");
    const [page, setPage] = useState<number>(1);
    const [page_size, setPageSize] = useState<number>(10);
    const [data, setData] = useState<LotDisplayType[]>([]);
    const [count, setCount] = useState<number>(0);
    const [minPrice, setMinPrice] = useState<number>(0);
    const [maxPrice, setMaxPrice] = useState<number>(10000);

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
            setMinPrice(Math.min(...result.map((lot: LotDisplayType) => lot.end_price)));
            setMaxPrice(Math.max(...result.map((lot: LotDisplayType) => lot.end_price)));
        };
        fetchData();
    }, [filters, order_by, page, page_size]);

    const handleExport = async () => {
        const payload = {
            filters: filters,
            order_by: "id"
          };
        
          const response = await fetch('http://localhost:5000/lot_export_csv', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
          });
        
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
        
          const link = document.createElement('a');
          link.href = url;
          link.download = 'lots_export.csv';
          document.body.appendChild(link);
          link.click();
          link.remove();
          window.URL.revokeObjectURL(url);
    };

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
      </HomeContainer>
    );
}

export default Home;