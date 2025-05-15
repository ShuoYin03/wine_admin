import { Column } from '@/components/DataTable/DataTable.type';

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
    id: number;
    external_id: string;
    auction_id: string;
    lot_name: string;
    unit?: number;
    volume?: number;
    lot_type?: string;
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
    lot_items?: Array<LotItemType>;
};

export type LotItemType = {
    id: number;
    lot_id: string;
    lot_producer?: string;
    vintage?: string;
    unit_format?: string;
    wine_colour?: string;
};

export type LotDisplayType = {
    id?: number;
    wine_name?: string;
    vintage?: number;
    region?: string;
    country?: string;
    unit?: number;
    colour?: string;
    currency?: string;
    start_price?: number;
    end_price?: number;
    sold?: boolean;
};

export const LotColumns: Column[] = [
    {
        header: "ID",
        accessor: "id",
    },
    {
        header: "Lot Name",
        accessor: "lot_name",
    },
    {
        header: "Region",
        accessor: "region",
    },
    {
        header: "Country",
        accessor: "country",
    },
    {
        header: "Units",
        accessor: "unit",
    },
    {
        header: "Currency",
        accessor: "currency",
    },
    {
        header: "Start Price",
        accessor: "start_price",
    },
    {
        header: "End Price",
        accessor: "end_price",
    },
    {
        header: "Sold",
        accessor: "sold",
    },
    {
        header: "Lot Items",
        accessor: "lot_items",
    }
]
    