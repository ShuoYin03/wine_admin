import React, { useState, useEffect, useRef } from "react";
import styled from "styled-components";
import SearchIcon from "@/assets/search.svg";
import FunnelIcon from "@/assets/funnel.svg";
import FilterWindow from "./FilterWindow";
import SquareButton from "../SquareButton/SquareButton";
import ArrowUpShort from "@/assets/arrow-up-short.svg";
import ArrowDownShort from "@/assets/arrow-down-short.svg";

type SearchBarProps = {
    callbackFilter: (filters: object) => void;
    callbackOrderBy: (orderBy: string) => void;
};

const SearchBarMainContainer = styled.div`
    display: flex;
    flex-direction: column;
    background-color: #FDF8F5;
`;

const SearchBarContainer = styled.div`
    display: flex;
    align-items: center;
    width: 100%;
    height: 45px;
`;

const SearchWrapper = styled.div`
    display: flex;
    align-items: center;
    width: 380px;
    height: 100%;
    border: 1px solid #705C61;
    border-radius: 10px;
    padding: 0 12px;
    background-color: #FDFCFB;
`;

const SearchIconWrapper = styled.div`
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 5px;
    padding-top: 2px;
    padding-left: 2px;

    svg {
        width: 18px;
        height: 18px;
        fill: #705C61;
    }
`;

const SearchInput = styled.input`
    flex: 1;
    height: 100%;
    border: none;
    font-size: 16px;
    outline: none;
    background-color: transparent;
    color: #333;

    &::placeholder {
        color: #705C61;
    }
`;

const SubmitButton = styled.button`
    width: 100px;
    height: 46px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    color: #ffffff;
    background-color: rgb(133, 56, 65);
    cursor: pointer;
    margin-left: 10px;

    &:hover {
        background-color: #722F37;
        transition: background-color 0.2s, color 0.2s;
    }
`;

const RightSideContainer = styled.div`
    display: flex;
    align-items: center;
    align-self: flex-end;
    margin-left: auto;
`;

const FilterButton = styled.button`
    display: flex;
    width: 110px;
    height: 46px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    background-color: #FDFCFB;
    border: 1px dashed #705C61;
    align-items: center;
    justify-content: center;
    cursor: pointer;

    &:hover {
        span {
            color: #ffffff;
        }
        svg {
            fill: #ffffff;
        }
        background-color: #996932;
        transition: background-color 0.2s, color 0.2s;
    }
`;

const FilterIconWrapper = styled.div`
    display: flex;
    margin-right: 8px;
    svg {
        width: 15px;
        height: 15px;
        fill: #705C61;
    }
`;

const FilterText = styled.span`
    color: #705C61;
    font-size: 16px;
`;

const SortWrapper = styled.div`
    display: flex;
    align-items: center;
    margin-left: 10px;
`;

const SortText = styled.span`
    font-size: 15px;
    color: #705C61;
    margin-right: 5px;
`;

const SortSelect = styled.select`
    width: 160px;
    height: 40px;
    border: 1px solid rgb(204, 199, 195);
    border-radius: 8px;
    background-color: #FDFCFB;
    color: #705C61;
    cursor: pointer;
    margin-right: 10px;
    outline: none;
    padding: 10px;

    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;

    background-image: url("data:image/svg+xml;utf8,<svg fill='%23705C61' height='14' viewBox='0 0 24 24' width='14' xmlns='http://www.w3.org/2000/svg'><path d='M7 10l5 5 5-5z'/></svg>");
    background-repeat: no-repeat;
    background-position: right 6px center;
    background-size: 14px;
`;

const ImportButton = styled.button`
    width: 100px;
    height: 46px;
    border: 1px solid rgb(204, 199, 195);
    border-radius: 8px;
    font-weight: 600;
    color: #705C61;
    background-color: #FDFCFB;
    cursor: pointer;
    margin-left: 10px;
    &:hover {
        color: #ffffff;
        background-color: #996932;
        transition: background-color 0.2s, color 0.2s;
    }
`;

const ExportButton = styled.button`
    width: 100px;
    height: 46px;
    border: 1px solid rgb(204, 199, 195);
    border-radius: 8px;
    font-weight: 600;
    color: #705C61;
    background-color: #FDFCFB;
    cursor: pointer;
    margin-left: 10px;
    &:hover {
        color: #ffffff;
        background-color: #996932;
        transition: background-color 0.2s, color 0.2s;
    }
`;

const SearchBar = ({ callbackFilter, callbackOrderBy }: SearchBarProps) => {
    const selectFilters = [
        "Auction House",
        "Lot Producer",
        "Region",
        "Colour",
        "Format",
        "Vintage",
        "Auction Before",
        "Auction After",
        "Price Range",
    ];

    const [showFilterWindow, setShowFilterWindow] = useState(false);
    const [sortField, setSortField] = useState("");
    const [sortDirection, setSortDirection] = useState("asc");
    const [filters, setFilters] = useState<Array<[string, string, string]>>([]);
    const [filterCount, setFilterCount] = useState<Record<string, number>>(
        selectFilters.map((filter) => [filter, 0]).reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {})
    );

    const toggleFilterWindow = () => {
        setShowFilterWindow(!showFilterWindow);
    };

    const handleSubmit = () => {
        console.log("Search submitted");
    };

    const handleSortDirectionChange = () => {
        setSortDirection((prevDirection) => (prevDirection === "asc" ? "desc" : "asc"));
    }

    const handleFilterChange = (
        filters: Array<[string, string, string]>, 
        count: Record<string, number>
    ) => {
        setFilters(filters);
        setFilterCount(count);
        callbackFilter(filters);
    };

    useEffect(() => {
        const sortDirectionSymbol = sortDirection === "asc" ? "" : "-";
        callbackOrderBy(`${sortDirectionSymbol}${sortField}`);
    }, [sortField, sortDirection]);

    return (
        <SearchBarMainContainer>
            <SearchBarContainer>
                <SearchWrapper>
                    <SearchIconWrapper>
                    <SearchIcon />
                    </SearchIconWrapper>
                    <SearchInput placeholder="Search lots by name, vintage, region..." />
                </SearchWrapper>
                <SubmitButton onClick={handleSubmit}>Search</SubmitButton>
                <RightSideContainer>
                    <FilterButton onMouseDown={(e) => {e.stopPropagation(); toggleFilterWindow();}}>
                        <FilterIconWrapper>
                            <FunnelIcon />
                        </FilterIconWrapper>
                        <FilterText>Filters</FilterText>
                    </FilterButton>
                    <SortWrapper>
                        <SortText>Sort by :</SortText>
                        <SortSelect onChange={(e) => setSortField(e.target.value)}>
                            <option value=""></option>
                            <option value="wine_name">Name</option>
                            <option value="vintage">Vintage</option>
                            <option value="region">Region</option>
                            <option value="end_price">Price</option>
                        </SortSelect>
                        <SquareButton onClick={handleSortDirectionChange}>
                            {sortDirection === "asc" ? (
                                <ArrowUpShort />
                            ) : (
                                <ArrowDownShort />
                            )}
                        </SquareButton>
                    </SortWrapper>
                    <ImportButton>Import</ImportButton>
                    <ExportButton>Export</ExportButton>
                </RightSideContainer>
            </SearchBarContainer>
            {showFilterWindow && 
                <FilterWindow 
                    callback={handleFilterChange}
                    onClose={() => toggleFilterWindow()}
                    filters={filters}
                    setFilters={setFilters}
                    filterCount={filterCount}
                    setFilterCount={setFilterCount}
                />}
        </SearchBarMainContainer>
  );
};

export default SearchBar;
