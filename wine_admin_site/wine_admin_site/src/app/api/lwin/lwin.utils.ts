import { LwinMatchingType } from "@/types/lwinApi";
import { LwinApiParams } from "@/types/lwinApi";

const createParamString = ({
    page, 
    page_size}: LwinApiParams
) => {
    const paramString = new URLSearchParams({
        ...(page && {page: page.toString()}),
        ...(page_size && {page_size: page_size.toString()}),
    }).toString();

    return paramString;
};

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

export { createParamString, filterData };