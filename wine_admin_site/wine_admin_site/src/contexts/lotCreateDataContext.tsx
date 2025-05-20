import { createDataContext } from '@/contexts/DataContext';
import { LotType } from '@/types/lotApi';

const extractPrice = (lot: LotType) => lot.end_price || 0;

export const {
  DataProvider: LotDataProvider,
  useDataContext: useLotDataContext,
} = createDataContext<LotType>(extractPrice);