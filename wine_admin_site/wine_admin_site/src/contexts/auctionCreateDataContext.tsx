import { createDataContext } from '@/contexts/DataContext';
import { AuctionType } from '@/types/auctionApi';

const extractPrice = (auction: AuctionType) => auction.sales.total_sales;

export const {
  DataProvider: AuctionDataProvider,
  useDataContext: useAuctionDataContext,
} = createDataContext<AuctionType>(extractPrice);