import { LotDisplayType } from '@/types/lotApi';

export type Column = {
    header: string;
    accessor: string;
};

export type TableProps = {
    columns: Column[];
    data: LotDisplayType[];
};