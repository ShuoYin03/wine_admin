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

export { createParamString };