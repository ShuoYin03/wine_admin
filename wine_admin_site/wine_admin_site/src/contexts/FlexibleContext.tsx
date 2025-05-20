import { useAuctionDataContext } from './auctionCreateDataContext';
import { useLotDataContext } from './lotCreateDataContext';

const flexibleContext = (type: string) => {
    if (type === 'auction') {
        return useAuctionDataContext;
    } else if (type === 'lot') {
        return useLotDataContext;
    } else {
        throw new Error(`Unknown type: ${type}`);
    }
}

export default flexibleContext;