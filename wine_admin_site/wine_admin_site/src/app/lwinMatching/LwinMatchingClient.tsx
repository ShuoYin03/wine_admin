'use client';
import React, { useState, useEffect } from "react";
import styled from "styled-components";
import { useRouter } from 'next/navigation';
import MainTitle from "@/components/MainTitle/MainTitle";
import SearchBar from "@/components/SearchBar/SearchBar";
import DataTable from "@/components/DataTable/DataTable";
import { LwinDisplayType, LwinMatchingColumns } from "@/types/lwinApi";
import DataTableBottom from "@/components/DataTable/DataTableBottom";
import SwitchFilter from "@/components/SwitchFilter/SwitchFilter";
import LwinInfo from "@/components/LwinInfo/LwinInfo";
import { FilterProvider, useFilterContext } from "@/contexts/FilterContext";
import { lwinMatchingFilterOptions, lwinMatchingOrderByOptions } from "./lwinMatching.utils";

const LwinMatchingContainer = styled.div`
    display: flex;
    flex-direction: column;
    background-color: #FDF8F5;
    padding: 0px 200px;
    padding-bottom: 90px;
    min-height: 82vh;
`;

type LwinMatchingClientProps = {
    initialData: LwinDisplayType[];
    initialCount: number;
    initialPage: number;
    initialPageSize: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    initialFilters: any[];
    initialOrderBy: string;
    counts: {
        exactCount: number;
        multiCount: number;
        notCount: number;
    };
};

const LwinMatchingContent = ({ initialData, initialCount, initialPage, initialPageSize, initialFilters, counts }: LwinMatchingClientProps) => {
    const { filters, setFilters, orderBy } = useFilterContext();
    const router = useRouter();
    const [, startTransition] = React.useTransition();
    
    // We synchronize our local page and pageSize
    const [page, setPage] = useState<number>(initialPage);
    const [page_size, setPageSize] = useState<number>(initialPageSize);

    // Sync selected option for SwitchFilter based on matched filter
    const getInitialSelectedOption = () => {
        const matchFilter = initialFilters.find(f => f[0] === "matched");
        if (!matchFilter) return "All Results";
        switch (matchFilter[2]) {
            case "exact_match": return "Exact Match";
            case "multi_match": return "Multi Match";
            case "not_match": return "Not Match";
            default: return "All Results";
        }
    };
    const [selectedOption, setSelectedOption] = useState<string>(getInitialSelectedOption());

    // Sync to URL when state changes
    useEffect(() => {
        const payload = {
            filters: JSON.stringify(filters),
            orderBy: orderBy,
            page: page.toString(),
            pageSize: page_size.toString(),
        };
        const params = new URLSearchParams();
        if (filters.length > 0) params.set('filters', payload.filters);
        if (orderBy) params.set('orderBy', payload.orderBy);
        if (page > 1) params.set('page', payload.page);
        if (page_size !== 10) params.set('pageSize', payload.pageSize);
        
        startTransition(() => {
            router.replace(`/lwinMatching?${params.toString()}`, { scroll: false });
        });
    }, [filters, orderBy, page, page_size, router]);

    const handlePageChange = (direction: boolean) => {
        if (direction && page < Math.ceil(initialCount / page_size)) {
            setPage(page + 1);
        } else if (!direction && page > 1) {
            setPage(page - 1);
        }
    }

    const handlePageSizeChange = (size: number) => {
        setPageSize(size);
        setPage(1);
    };

    const handleSelectChange = (option: string) => {
        setFilters((prevFilters) => {
            const clearedFilters = prevFilters.filter((filter) => filter[0] !== "matched");
            switch (option) {
                case "Exact Match":
                    return [...clearedFilters, ["matched", "eq", "exact_match"]];
                case "Multi Match":
                    return [...clearedFilters, ["matched", "eq", "multi_match"]];
                case "Not Match":
                    return [...clearedFilters, ["matched", "eq", "not_match"]];
                case "All Results":
                default:
                    return clearedFilters;
            }
        });
        setSelectedOption(option);
        setPage(1);
    };

    return (
        <LwinMatchingContainer>
            <MainTitle title={"Lwin Matching"} subtitle={"Browse, Search, and Manage Lwin Matching Results"}></MainTitle>
            <LwinInfo 
                totalLwinCount={counts.exactCount + counts.multiCount + counts.notCount} 
                exactMatchCount={counts.exactCount} 
                multiMatchCount={counts.multiCount} 
                notMatchCount={counts.notCount}
            />
            <SwitchFilter options={["All Results", "Exact Match", "Multi Match", "Not Match"]} selectedOption={selectedOption} onSelect={handleSelectChange}></SwitchFilter>
            <SearchBar type='lwin'/>
            <DataTable<LwinDisplayType> columns={LwinMatchingColumns} data={initialData} />
            <DataTableBottom page={page} setPage={setPage} pageSize={page_size} setPageSize={setPageSize} handlePageChange={handlePageChange} handlePageSizeChange={handlePageSizeChange} count={initialCount}/>
        </LwinMatchingContainer>
    );
};

export default function LwinMatchingClient(props: LwinMatchingClientProps) {
    const defaultFilters = props.initialFilters.length > 0 ? props.initialFilters : [["matched", "eq", "exact_match"]];
    
    return (
        <FilterProvider 
            filterOptions={lwinMatchingFilterOptions} 
            orderByOptions={lwinMatchingOrderByOptions}
            initialFilters={defaultFilters}
            initialOrderBy={props.initialOrderBy}
        >
            <LwinMatchingContent {...props} initialFilters={defaultFilters} />
        </FilterProvider>
    );
}
