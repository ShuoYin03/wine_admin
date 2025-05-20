import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
    const { searchParams } = new URL(req.url);
    const paramString = searchParams.toString();
    const response = await fetch(`http://localhost:5000/auction?${paramString}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    });

    const data = await response.json(); 
    
    return NextResponse.json({ result: data });
}

export async function POST(req: NextRequest) {
    const payload = await req.json();

    const response = await fetch(`http://localhost:5000/auction_query_with_sales`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    const data = await response.json(); 
    const auctions = data.auctions;
    const count = data.count;
    
    return NextResponse.json({ result: auctions, count: count });
}
