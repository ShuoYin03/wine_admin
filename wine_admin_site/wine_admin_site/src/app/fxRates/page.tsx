'use client'
import React, { useEffect } from "react";
import styled from "styled-components";
import MainTitle from "@/components/MainTitle/MainTitle";
import DataTable from "@/components/DataTable/DataTable";
import { RatesDisplayType } from "@/types/ratesApi";
import { RatesColumns } from "@/types/ratesApi";

const FxRatesContainer = styled.div`
    display: flex;
    flex-direction: column;
    background-color: #FDF8F5;
    padding: 0px 200px;
    padding-bottom: 90px;
    min-height: 82vh;
`;

const FxRates = () => {
    const [data, setData] = React.useState<RatesDisplayType[]>([]);

    useEffect(() => {
        const fetchData = async () => {
            const response = await fetch('/api/fxRates', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            const data = await response.json();
            const { result } = data;
            setData(result.data);
        };

        fetchData();
    }, []);

    return (
        <FxRatesContainer>
            <MainTitle title="FX Rates" subtitle="FX Rates On The Current Date" />
            <DataTable columns={RatesColumns} data={data}/>
        </FxRatesContainer>
    )
};

export default FxRates;