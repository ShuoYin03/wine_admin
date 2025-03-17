import { NextRequest, NextResponse } from 'next/server';
import { createParamString, filterData } from './lot.utils';
import { LotApiParams } from '@/types/lotApi';

export async function GET(req: NextRequest) {
    const params = Object.fromEntries(req.nextUrl.searchParams.entries());
    const page = Number(params.page) || undefined;
    const page_size = Number(params.page_size) || undefined;

    const lotApiParams: LotApiParams = {
        page,
        page_size
    };

    const paramString = createParamString(lotApiParams);
    const response = await fetch(`http://localhost:5000/query_all?${paramString}`);
    const data = await response.json();

    const filtered_data = filterData(data);

    return NextResponse.json({ result: filtered_data });
}

export async function POST(req: NextRequest) {
    const payload = await req.json();

    const response = await fetch(`http://localhost:5000/query`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    const data = await response.json();

    const filtered_data = filterData(data);

    return NextResponse.json({ result: filtered_data });
}
