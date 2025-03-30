'use client';
import React, { useState, useEffect} from 'react';
import styled from 'styled-components';
import SearchBar from '@/components/SearchBar/SearchBar';
import LotsTable from '@/components/LotsTable/LotsTable';
import SquareButton from '@/components/SquareButton/SquareButton';
import { LotDisplayType } from '@/types/lotApi';
import { Column } from '@/components/LotsTable/LotsTable.type';
import ChevronLeft from '@/assets/chevron-left.svg';
import ChevronRight from '@/assets/chevron-right.svg';
import ChevronDoubleLeft from '@/assets/chevron-double-left.svg';
import ChevronDoubleRight from '@/assets/chevron-double-right.svg';

const HomeContainer = styled.div`
    display: flex;
    flex-direction: column;
    background-color: #FDF8F5;
    padding: 0px 200px;
    padding-bottom: 90px;
`;

const HomeTitle = styled.h1`
    font-size: 2rem;
    color: #722F37;
    height: 10px;
    padding-top: 20px;
`;

const HomeSubtitle = styled.p`
    font-size: 15px;
    color: #705C61;
    margin-bottom: 40px;
`;

const TableBottomContainer = styled.div`
    display: flex;
    width: 100%;
    height: 50px;
    margin-top: 15px;
    align-items: center;
    justify-content: flex-start;
    font-size: 15px;
`;

const DisplayPageSize = styled.div`
    display: flex;
    color: #705C61;
`;

const PageSizeSwitchContainer = styled.div`
    display: flex;
    align-items: center;
    justify-content: center;
    margin-left: 20px;
`;

const PageSizeText = styled.span`
    display: flex;
    color:rgb(90, 74, 78);
    font-weight: 600;
`;

const PageSizeSwitcher = styled.select`
    display: flex;
    margin-left: 20px;
    padding: 10px;
    width: 80px;
    height: 35px;
    color: #705C61;
    border-radius: 8px;
    background-color: ##FEFAF9;
    outline: none;

    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;

    background-image: url("data:image/svg+xml;utf8,<svg fill='%23705C61' height='14' viewBox='0 0 24 24' width='14' xmlns='http://www.w3.org/2000/svg'><path d='M7 10l5 5 5-5z'/></svg>");
    background-repeat: no-repeat;
    background-position: right 6px center;
    background-size: 14px;
`;

const PageSwitchContainer = styled.div`
    display: flex;
    flex: 1;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
`;

const DisplayPage = styled.div`
    color: #705C61;
`;

const fakeColumns: Column[] = [
    {
        header: "ID",
        accessor: "id",
    },
    {
        header: "Wine Name",
        accessor: "wine_name",
    },
    {
        header: "Vintage",
        accessor: "vintage",
    },
    {
        header: "Units",
        accessor: "unit",
    },
    {
        header: "End Price",
        accessor: "end_price",
    },
    {
        header: "Sold",
        accessor: "sold",
    },
]
const fakeData: LotDisplayType[] = [
    {
        id: 1,
    },
    {
        id: 2,
    },
    {
        id: 3,
        wine_name: "Wine C",
        vintage: 2020,
        unit: 3,
        end_price: 75,
        sold: true,
    },
    {
        id: 4,
        wine_name: "Wine D",
        vintage: 2016,
        unit: 1,
        end_price: 150,
        sold: false,
    },
    {
        id: 5,
        wine_name: "Wine E",
        vintage: 2019,
        unit: 6,
        end_price: 200,
        sold: true,
    },
    {
        id: 6,
        wine_name: "Wine F",
        vintage: 2021,
        unit: 12,
        end_price: 300,
        sold: false,
    },
    {
        id: 7,
        wine_name: "Wine G",
        vintage: 2018,
        unit: 2,
        end_price: 50,
        sold: true,
    },
    {
        id: 8,
        wine_name: "Wine H",
        vintage: 2017,
        unit: 4,
        end_price: 125,
        sold: false,
    },
    {
        id: 9,
        wine_name: "Wine I",
        vintage: 2022,
        unit: 8,
        end_price: 175,
        sold: true,
    },
    {
        id: 10,
        wine_name: "Wine J",
        vintage: 2015,
        unit: 10,
        end_price: 250,
        sold: false,
    },
    {
        id: 11,
        wine_name: "Wine K",
        vintage: 2020,
        unit: 5,
        end_price: 80,
        sold: true,
    },
    {
        id: 12,
        wine_name: "Wine L",
        vintage: 2019,
        unit: 7,
        end_price: 120,
        sold: false,
    },
    {
        id: 13,
        wine_name: "Wine M",
        vintage: 2021,
        unit: 9,
        end_price: 180,
        sold: true,
    },
    {
        id: 14,
        wine_name: "Wine N",
        vintage: 2018,
        unit: 11,
        end_price: 220,
        sold: false,
    },
    {
        id: 15,
        wine_name: "Wine O",
        vintage: 2017,
        unit: 13,
        end_price: 300,
        sold: true,
    },
    {
        id: 16,
        wine_name: "Wine P",
        vintage: 2016,
        unit: 15,
        end_price: 400,
        sold: false,
    },
  ]

const Home = () => {
    const [filters, setFilters] = useState<object>({});
    const [order_by, setOrderBy] = useState<object>({});
    const [page, setPage] = useState<number>(1);
    const [page_size, setPageSize] = useState<number>(30);
    const [data, setData] = useState<LotDisplayType[]>(fakeData);

    useEffect(() => {
        const fetchData = async () => {
            const payload = {
                filters: filters,
                order_by: order_by,
                page: page,
                page_size: page_size
            };
            const response = await fetch('/api/lot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            const data = await response.json();
            const { result } = data;
            setData(result);
        };
        fetchData();
    }, [filters, order_by, page, page_size]);

    const handlePageChange = (direction: boolean) => {
        if (direction && page < Math.ceil(data.length / page_size)) {
            setPage(page + 1);
        } else if (page > 1) {
            setPage(page - 1);
        }
    }

    const handleFilterChange = (filters: object) => {
        setFilters(filters);
    }
    const handleOrderByChange = (orderBy: object) => {
        setOrderBy(orderBy);
    }


    return (
      <HomeContainer>
        <HomeTitle>Wine Admin Site</HomeTitle>
        <HomeSubtitle>Browse, Search, and Manage Wine Lots</HomeSubtitle>
        <SearchBar callbackFilter={handleFilterChange} callbackOrderBy={handleOrderByChange}/>
        <LotsTable columns={fakeColumns} data={fakeData} />
        <TableBottomContainer>
          <DisplayPageSize>
              Displaying {page * page_size - page_size + 1} - {Math.min(page * page_size, data.length)} of {data.length} results
          </DisplayPageSize>
          <PageSizeSwitchContainer>
            <PageSizeText>
                Lots per page:
            </PageSizeText>
            <PageSizeSwitcher
                value={page_size}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                }}
                >
                {[10, 20, 50, 100].map((size) => (
                  <option key={size} value={size}>
                        {size}
                    </option>
                ))}
            </PageSizeSwitcher>
          </PageSizeSwitchContainer>
          <PageSwitchContainer>
            <SquareButton onClick={() => setPage(1)}><ChevronDoubleLeft /></SquareButton>
            <SquareButton onClick={() => handlePageChange(false)}><ChevronLeft /></SquareButton>
            <DisplayPage>
                Page {page} of {Math.ceil(data.length / page_size)}
            </DisplayPage>
            <SquareButton onClick={() => handlePageChange(true)}><ChevronRight /></SquareButton>
            <SquareButton onClick={() => setPage(1)}><ChevronDoubleRight /></SquareButton>
          </PageSwitchContainer>
        </TableBottomContainer>
      </HomeContainer>
    );
}

export default Home;