export interface LotApiParams {
    page?: number;
    page_size?: number;
};

export interface LotApiPayload {
    filters?: object;
    order_by?: Array<string>;
    page?: number;
    page_size?: number;
};

export type LotType = {
    id: string;
    auction_id: number;
    lot_producer?: string;
    wine_name: string;
    vintage?: string;
    unit_format?: string;
    unit?: number;
    volumn?: number;
    lot_type?: string;
    wine_type?: string;
    original_currency: string;
    start_price: number;
    end_price?: number;
    low_estimate: number;
    high_estimate: number;
    sold: boolean;
    region?: string;
    sub_region?: string;
    country?: string;
    success: boolean;
    url: string;
};

export type LotDisplayType = {
    wine_name: string;
    vintage?: string;
    unit?: number;
    end_price?: number;
    sold: boolean;
};
    