import { LotType } from '@/types/lotApi';

export const filterData = (
    lot: Array<LotType>
) => {
    const filtered_data = lot.map((lot: LotType) => ({
        id: lot.id,
        lot_name: lot.lot_name,
        region: lot.region,
        country: lot.country,
        unit: lot.unit,
        currency: lot.original_currency,
        start_price: lot.start_price,
        end_price: lot.end_price,
        sold: lot.sold,
    }));

    return filtered_data;
};