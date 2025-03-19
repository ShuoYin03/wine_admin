export interface LwinApiParams {
    page?: number;
    page_size?: number;
};

export enum MatchStatusType {
    EXACT_MATCH = 'exact_match',
    MULTI_MATCH = 'multi_match',
    NOT_MATCH = 'not_match',
};

export type LwinDisplayType = {
    lwin: string;
    wine_name: string;
    vintage?: string;
    unit?: number;
    match_status: MatchStatusType;
};