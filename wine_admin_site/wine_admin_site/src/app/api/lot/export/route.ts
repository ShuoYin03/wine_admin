import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest): Promise<NextResponse> {
    const payload = await req.json();

    const response = await fetch(`${process.env.PYTHON_API_URL}/lot_export_csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    const blob = await response.blob();
    return new NextResponse(blob, {
        headers: {
            'Content-Type': response.headers.get('Content-Type') ?? 'text/csv',
            'Content-Disposition':
                response.headers.get('Content-Disposition') ?? 'attachment; filename="lots.csv"',
        },
    });
}
