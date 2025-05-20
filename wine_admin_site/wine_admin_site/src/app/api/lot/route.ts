import { NextRequest, NextResponse } from 'next/server';
import { filterData } from './lot.utils';

export async function POST(req: NextRequest) {
    const payload = await req.json();

    const response = await fetch(`http://localhost:5000/lot_query`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    const data = await response.json(); 
    const lots = data.lots;
    const count = data.count;
    
    const filtered_data = filterData(lots);
    
    return NextResponse.json({ result: filtered_data, count: count });
}
