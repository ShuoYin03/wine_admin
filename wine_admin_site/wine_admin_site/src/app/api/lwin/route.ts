import { NextRequest, NextResponse } from 'next/server';
import { filterData } from './lwin.utils';

export async function POST(req: NextRequest) {
    const payload = await req.json();

    const response = await fetch(`http://localhost:5000/lwin_and_lots_query`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    const data = await response.json();
    const lwins = data.data;
    const count = data.count;

    const filtered_data = filterData(lwins);

    return NextResponse.json({ result: filtered_data, count: count });
}