import { useAuctionDataContext } from './auctionCreateDataContext';
import { useLotDataContext } from './lotCreateDataContext';

const useNullDataContext = () => ({ data: [], setData: () => {}, maxPrice: 0, minPrice: 0 });

const flexibleContext = (type: string) => {
    if (type === 'auction') {
        return useAuctionDataContext;
    } else if (type === 'lot') {
        return useLotDataContext;
    } else {
        return useNullDataContext;
    }
}

export default flexibleContext;