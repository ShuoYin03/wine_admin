import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
    const response = await fetch(`http://localhost:5000/rates_query?`);
    const data = await response.json();

    return NextResponse.json({ result: data });
}