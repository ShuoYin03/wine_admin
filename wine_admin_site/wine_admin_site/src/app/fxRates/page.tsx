import React from 'react';
import FxRatesClient from './FxRatesClient';
import { RatesDisplayType } from '@/types/ratesApi';

export const metadata = {
    title: 'FX Rates - Wine Admin Site',
};

export default async function FxRatesPage() {
    let data: RatesDisplayType[] = [];

    try {
        const response = await fetch(`${process.env.PYTHON_API_URL}/rates_query`, {
            cache: 'no-store',
        });
        if (response.ok) {
            const raw = await response.json();
            data = raw.data ?? [];
        }
    } catch (e) {
        console.error('Failed to fetch fx rates', e);
    }

    return <FxRatesClient data={data} />;
}