import { Column } from '@/components/DataTable/DataTable.type';

export enum MatchStatusType {
    EXACT_MATCH = 'exact_match',
    MULTI_MATCH = 'multi_match',
    NOT_MATCH = 'not_match',
};

export type LwinMatchingType = {
    id: string;
    wine_name: string;
    matched: string;
    lwin?: number[];
    match_score?: number[];
    match_item?: Record<string, string>[];
}

export type LwinDisplayType = {
    wine_name: string;
    lwin: string[];
    match_score: number[];
    match_status: MatchStatusType;
};

export const LwinMatchingColumns: Column[] = [
    {
        header: "ID",
        accessor: "id",
    },
    {
        header: "Wine Name",
        accessor: "wine_name",
    },
    {
        header: "Lwin",
        accessor: "lwin",
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