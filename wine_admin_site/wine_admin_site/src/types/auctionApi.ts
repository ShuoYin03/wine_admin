import { Column } from '@/components/DataTable/DataTable.type';
import { AuctionSalesType } from './auctionSalesApi';

export type AuctionType = {
    id: number;
    external_id: string;
    auction_title: string;
    auction_house: string;
    city: string;
    continent: string;
    start_date: Date;
    end_date: Date;
    year: number;
    quarter: number;
    auction_type: string;
    url: string;
    sales: AuctionSalesType;
};

export const AuctionColumns: Column[] = [
    {
        header: "ID",
        accessor: "id",
    },
    {
        header: "Auction Title",
        accessor: "auction_title",
    },
    {
        header: "Auction House",
        accessor: "auction_house",
    },
    {
        header: "City",
        accessor: "city",
    },
    {
        header: "Continent",
        accessor: "continent",
    },
    {
        header: "Start Date",
        accessor: "start_date",
    },
    {
        header: "End Date",
        accessor: "end_date",
    },
    {
        header: "Auction Type",
        accessor: "auction_type",
    },
    {
        header: "URL",
        accessor: "url",
    },
]