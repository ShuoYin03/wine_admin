import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
    const payload = await req.json();

    const response = await fetch(`http://localhost:5000/match`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    const rawData = await response.text();
    const data = JSON.parse(rawData.replace(/NaN/g, 'null'));
    
    return NextResponse.json({ result: data });
}
