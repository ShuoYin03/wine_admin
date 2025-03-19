'use client';
import styled from 'styled-components';
import { LotDisplayType } from '@/types/lotApi';
import React, { useEffect, useState } from 'react';
import LotsTable from "@/components/LotsTable/LotsTable";

const Container = styled.div`
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
`;

const TableContainer = styled.div`
    display: flex;
    flex-direction: column;
    justify-content: center;
    width: 80%;
`;

const PageSwitchContainer = styled.div`
    display: flex;
    justify-content: center;
    margin-top: 20px;

    &:hover {
        background-color:rgba(255, 255, 255, 0.31);
        color: black;
    }
`;
const PageSwitch = styled.span`
    display: flex;
    justify-content: center;
    margin: 0 20px;
`;

export default function Lots() {
    const [page, setPage] = useState<number>(1);
    const [pageSize, setPageSize] = useState<number>(10);
    const [data, setData] = useState<LotDisplayType[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);

            try {
                const response = await fetch(`/api/lot?page=${page}&page_size=${pageSize}`);
                if (!response.ok) {
                    throw new Error(`Failed to fetch data: ${response.statusText}`);
                }
                
                const result = await response.json();
                setData(result.result);
            } catch (err) {
                console.error('Error fetching data:', err);
                setError('Failed to load data.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [page]);

    const handlePageChange = (pageChange: boolean) => {
        if (pageChange) {
            setPage(page + 1);
        } else if (page > 1) {
            setPage(page - 1);
        }
    }

    const helper = () => {
        console.log(data);
    }

    return (
        <Container>
            <TableContainer>
                <h1 onClick={helper}>Lots</h1>
                {loading && <p>Loading...</p>}
                {error && <p style={{ color: 'red' }}>{error}</p>}
                {!loading && !error && <LotsTable columns={Object.keys(data[0])} data={data} />}
                <PageSwitchContainer>
                    <PageSwitch onClick={() => handlePageChange(false)}>Previous</PageSwitch>
                    {page}
                    <PageSwitch onClick={() => handlePageChange(true)}>Next</PageSwitch>
                </PageSwitchContainer>
            </TableContainer>

            
        </Container>
    );
};