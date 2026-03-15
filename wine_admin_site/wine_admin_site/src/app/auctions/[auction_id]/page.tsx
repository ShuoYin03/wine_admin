import React from 'react';
import AuctionDetailClient from './AuctionDetailClient';
import Container from '@/components/Container/Container';

export const metadata = {
  title: 'Auction Detail - Wine Admin Site'
};

export default async function AuctionDetailPage(props: { params: Promise<{ auction_id: string }> }) {
    const params = await props.params;
    const { auction_id } = params;

    let data = null;

    try {
        const response = await fetch(`http://localhost:5000/auction/${auction_id}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Include-Lots': 'true',
            },
            cache: 'no-store'
        });
        
        if (response.ok) {
            const rawData = await response.json();
            data = rawData.auction || rawData;
        }
    } catch (e) {
        console.error("Failed to fetch auction details", e);
    }

    if (!data) return <Container>Loading...</Container>;

    return <AuctionDetailClient data={data} />;
}
