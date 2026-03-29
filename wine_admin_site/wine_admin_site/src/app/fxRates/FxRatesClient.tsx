'use client';
import React from 'react';
import styled from 'styled-components';
import MainTitle from '@/components/MainTitle/MainTitle';
import DataTable from '@/components/DataTable/DataTable';
import { RatesDisplayType, RatesColumns } from '@/types/ratesApi';

const FxRatesContainer = styled.div`
    display: flex;
    flex-direction: column;
    background-color: #FDF8F5;
    padding: 0px 200px;
    padding-bottom: 90px;
    min-height: 82vh;
`;

type FxRatesClientProps = {
    data: RatesDisplayType[];
};

const FxRatesClient = ({ data }: FxRatesClientProps) => {
    return (
        <FxRatesContainer>
            <MainTitle title="FX Rates" subtitle="FX Rates On The Current Date" />
            <DataTable columns={RatesColumns} data={data} />
        </FxRatesContainer>
    );
};

export default FxRatesClient;
