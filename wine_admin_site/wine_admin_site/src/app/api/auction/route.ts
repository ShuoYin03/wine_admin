import { NextRequest, NextResponse } from 'next/server';
import { AuctionType } from '@/types/auctionApi';

type AuctionsResponse = {
    auctions: AuctionType[];
    count: number;
};

export async function GET(_req: NextRequest): Promise<NextResponse<{ result: AuctionType[] }>> {
    const response = await fetch(`http://127.0.0.1:5000/auctions`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    });

    const data: AuctionsResponse = await response.json();
    return NextResponse.json({ result: data.auctions });
}

export async function POST(req: NextRequest): Promise<NextResponse<{ result: AuctionType[]; count: number }>> {
    const payload: unknown = await req.json();

    const response = await fetch(`http://127.0.0.1:5000/auctions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    const data: AuctionsResponse = await response.json();
    return NextResponse.json({ result: data.auctions, count: data.count });
}
