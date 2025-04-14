import { LotApiParams, LotType } from '@/types/lotApi';
import { start } from 'repl';

const createParamString = ({
    page, 
    page_size}: LotApiParams
) => {
    const paramString = new URLSearchParams({
        ...(page && {page: page.toString()}),
        ...(page_size && {page_size: page_size.toString()}),
    }).toString();

    return paramString;
};

const filterData = (
    lot: Array<LotType>
) => {
    const filtered_data = lot.map((lot: LotType) => ({
        wine_name: lot.wine_name,
        vintage: lot.vintage,
        region: lot.region,
        country: lot.country,
        unit: lot.unit,
        colour: lot.wine_type,
        currency: lot.original_currency,
        start_price: lot.start_price,
        end_price: lot.end_price,
        sold: lot.sold
    }));

    return filtered_data;
};

export { createParamString, filterData };