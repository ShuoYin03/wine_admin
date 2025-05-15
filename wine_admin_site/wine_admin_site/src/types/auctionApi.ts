type AuctionType = {
    id: string;
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
};

export type { AuctionType };