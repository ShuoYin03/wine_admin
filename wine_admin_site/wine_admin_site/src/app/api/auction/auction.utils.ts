import { AuctionType } from '@/types/auctionApi';

const filterData = (
    auction: Array<AuctionType>
) => {
    const filtered_data = auction.map((auction: AuctionType) => ({
        id: auction.id,
        auction_title: auction.auction_title,
        auction_house: auction.auction_house,
        city: auction.city,
        continent: auction.continent,
        start_date: auction.start_date,
        end_date: auction.end_date,
        year: auction.year,
        quarter: auction.quarter,
        auction_type: auction.auction_type,
        url: auction.url,
        sales: auction.sales,
    }));

    return filtered_data;
};

export { filterData };