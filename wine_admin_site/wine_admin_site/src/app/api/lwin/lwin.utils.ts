import { LwinMatchingType, LwinDisplayType, MatchStatusType } from "@/types/lwinApi";

const filterData = (
    lwin: LwinMatchingType[]
): LwinDisplayType[] => {
    const filtered_data = lwin.map((lwin: LwinMatchingType) => ({
        id: lwin.id,
        lot_name: lwin.lot_name,
        lwin: lwin.lwin || [],
        lwin11: lwin.lwin_11 || [],
        match_status: (lwin.matched as MatchStatusType) || MatchStatusType.NOT_MATCH,
        match_score: lwin.match_score || [],
    }));

    return filtered_data;
};

export { filterData };