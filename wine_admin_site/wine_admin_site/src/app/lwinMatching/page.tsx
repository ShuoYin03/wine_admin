'use client'
import React, { useState, useEffect} from "react"
import styled from "styled-components"
import MainTitle from "@/components/MainTitle/MainTitle"
import SearchBar from "@/components/SearchBar/SearchBar"
import DataTable from "@/components/DataTable/DataTable"
import { LwinDisplayType } from "@/types/lwinApi"
import { LwinMatchingColumns } from "@/types/lwinApi"
import DataTableBottom from "@/components/DataTable/DataTableBottom"
import SwitchFilter from "@/components/SwitchFilter/SwitchFilter"
import LwinInfo from "@/components/LwinInfo/LwinInfo"

const LwinMatchingContainer = styled.div`
    display: flex;
    flex-direction: column;
    background-color: #FDF8F5;
    padding: 0px 200px;
    padding-bottom: 90px;
    min-height: 82vh;
`;

const LwinMatching = () => {
    const [filters, setFilters] = useState<[string, string, string][]>([["matched", "eq", "exact_match"]]);
    const [order_by, setOrderBy] = useState<string>("");
    const [page, setPage] = useState<number>(1);
    const [page_size, setPageSize] = useState<number>(10);
    const [data, setData] = useState<LwinDisplayType[]>([]);
    const [count, setCount] = useState<number>(0);
    const [exactCount, setExactCount] = useState<number>(10);
    const [multiCount, setMultiCount] = useState<number>(10);
    const [NotCount, setNotCount] = useState<number>(10);
    const [selectedOption, setSelectedOption] = useState<string>("All Results");

    useEffect(() => {
        const fetchData = async () => {
            const payload = {
                filters: filters,
                order_by: order_by,
                page: page,
                page_size: page_size,
                return_count: true,
            };

            const response = await fetch('/api/lwin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            
            const data = await response.json();
            const { result, count } = data;
            setData(result);
            setCount(count);
        };

        const fetchCount = async () => {
            const response = await fetch('/api/lwin/count', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            const data = await response.json();
            const { result } = data;
            setExactCount(result.data.exact_match_count);
            setMultiCount(result.data.multi_match_count);
            setNotCount(result.data.not_match_count);
        }
        fetchData();
        fetchCount();
    }, [filters, order_by, page, page_size]);

    const handlePageChange = (direction: boolean) => {
        if (direction && page < Math.ceil(count / page_size)) {
            setPage(page + 1);
        } else if (!direction && page > 1) {
            setPage(page - 1);
        }
    }

    const handleFilterChange = (newFilters: [string, string, string][]) => {
        setFilters(newFilters);
        setPage(1);
    };

    const handleOrderByChange = (newOrderBy: string) => {
        setOrderBy(newOrderBy);
        setPage(1);
    };

    const handleSelectChange = (selectedOption: string) => {
        setFilters((prevFilters) => {
            const clearedFilters = prevFilters.filter((filter) => filter[0] !== "matched");
            
            switch (selectedOption) {
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
    
        setSelectedOption(selectedOption);
        setPage(1);
    };

    return (
        <LwinMatchingContainer>
            <MainTitle title={"Lwin Matching"} subtitle={"Browse, Search, and Manage Lwin Matching Results"}></MainTitle>
            <LwinInfo totalLwinCount={exactCount + multiCount + NotCount} exactMatchCount={exactCount} multiMatchCount={multiCount} notMatchCount={NotCount}/>
            <SwitchFilter options={["All Results", "Exact Match", "Multi Match", "Not Match"]} selectedOption={selectedOption} onSelect={handleSelectChange}></SwitchFilter>
            <SearchBar callbackFilter={handleFilterChange} callbackOrderBy={handleOrderByChange}/>
            <DataTable<LwinDisplayType> columns={LwinMatchingColumns} data={data} />
            <DataTableBottom page={page} setPage={setPage} pageSize={page_size} setPageSize={setPageSize} handlePageChange={handlePageChange} count={count}/>
        </LwinMatchingContainer>
    );
}

export default LwinMatching;