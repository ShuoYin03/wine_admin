import { Column } from '@/components/DataTable/DataTable.type';

export enum MatchStatusType {
    EXACT_MATCH = 'exact_match',
    MULTI_MATCH = 'multi_match',
    NOT_MATCH = 'not_match',
};

export type LwinMatchingType = {
    id: number;
    lot_id: string;
    lot_name: string;
    matched: string;
    lwin?: number[];
    lwin_11?: number[];
    match_score?: number[];
    match_item?: Record<string, string>[];
}

export type LwinDisplayType = {
    id: number;
    lot_name: string;
    lwin: number[];
    lwin11: number[];
    match_score: number[];
    match_status: MatchStatusType;
};

export const LwinMatchingColumns: Column[] = [
    {
        header: "ID",
        accessor: "id",
    },
    {
        header: "Lot Name",
        accessor: "lot_name",
    },
    {
        header: "Lwin",
        accessor: "lwin",
    },
    {
        header: "Lwin 11",
        accessor: "lwin_11",
    },
    {
        header: "Maching Score",
        accessor: "match_score",
    },
    {
        header: "Matching Status",
        accessor: "match_status",
    },
]