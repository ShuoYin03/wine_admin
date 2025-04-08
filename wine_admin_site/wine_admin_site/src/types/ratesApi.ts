import { Column } from '@/components/DataTable/DataTable.type';

export type RatesDisplayType = {
    id: number;
    rates_from: string;
    rates_to: string;
    rates: number;
};

export const RatesColumns: Column[] = [
    {
        header: "ID",
        accessor: "id",
    },
    {
        header: "Rates From",
        accessor: "rates_from",
    },
    {
        header: "Rates To",
        accessor: "rates_to",
    },
    {
        header: "Rates",
        accessor: "rates",
    }
]