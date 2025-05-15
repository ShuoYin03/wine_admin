import { LwinMatchingType } from "@/types/lwinApi";

const filterData = (
    lwin: LwinMatchingType[]
) => {
    const filtered_data = lwin.map((lwin: LwinMatchingType) => ({
        id: lwin.id,
        lot_name: lwin.lot_name,
        lwin: lwin.lwin,
        lwin11: lwin.lwin_11,
        match_status: lwin.matched,
        match_score: lwin.match_score,
    }));

    return filtered_data;
};

export { filterData };