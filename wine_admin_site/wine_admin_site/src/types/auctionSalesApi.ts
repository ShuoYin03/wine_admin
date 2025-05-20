export type AuctionSalesType = {
    id: number;
    auction_id: string;
    lots: number;
    sold: number;
    currency: string;
    total_low_estimate: number;
    total_high_estimate: number;
    total_sales: number;
    volume_sold: number;
    value_sold: number;
    top_lot: string;
    sale_type: string;
    single_cellar: boolean;
    ex_ch: boolean;
};