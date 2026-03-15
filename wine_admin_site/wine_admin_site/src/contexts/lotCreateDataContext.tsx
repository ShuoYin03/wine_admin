import { createDataContext } from '@/contexts/DataContext';
import { LotDisplayType } from '@/types/lotApi';

const extractPrice = (lot: LotDisplayType) => lot.end_price || 0;

export const {
  DataProvider: LotDataProvider,
  useDataContext: useLotDataContext,
} = createDataContext<LotDisplayType>(extractPrice);