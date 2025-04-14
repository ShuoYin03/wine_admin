import { LwinMatchingType } from "@/types/lwinApi";

const filterData = (
    lwin: LwinMatchingType[]
) => {
    const filtered_data = lwin.map((lwin: LwinMatchingType) => ({
        wine_name: lwin.wine_name,
        lwin: lwin.lwin,
        match_status: lwin.matched,
        match_score: lwin.match_score,
    }));

    return filtered_data;
};

export { filterData };