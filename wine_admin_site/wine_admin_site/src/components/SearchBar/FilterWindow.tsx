'use client';
import React, { useState, useEffect, useRef } from "react";
import styled from "styled-components";
import FilterOptions from "./FilterOptions";
import Count from "../Count/Count";
import dayjs, { Dayjs } from "dayjs";
import { 
    toggleFilter, 
    toggleDateFilter,
    togglePriceRangeFilter
} from "@/utils/toggleFilter";
import { keyMap } from "@/utils/data";
import FullCalendar from "../Calendar/FullCalendar";
import CustomYearCalendar from "../Calendar/CustomYearCalendar";
import PriceRange from "../PriceRange/PriceRange";

const FilterWindowContainer = styled.div`
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    width: 230px;
    height: 420px;
    padding: 0px 5px;
    margin-top: 50px;
    margin-left: 675px;
    background-color: #FDFCFB;
    border-radius: 8px;
    border: 1px solid rgb(204, 199, 195);
    position: absolute;
    z-index: 1000;
    overflow-y: auto;
    overflow-x: hidden;

    &::-webkit-scrollbar {
        width: 8px;
        background-color: #FDFCFB;
    }
`;

const SelectFilter = styled.button`
    position: relative;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    width: 230px;
    height: 35px;
    border-radius: 4px;
    border: 1px solid rgb(204, 199, 195);
    background-color: #F5F1ED;
    color: #705C61;
    margin-top: 6px;
    padding: 0px 7px;
    font-size: 14px;
    font-weight: 400;

    &:focus {
        outline: none;
        border-color: #996932;
        transition: border-color 0.2s;
    }

    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;

    background-image: url("data:image/svg+xml;utf8,<svg fill='%23705C61' height='14' viewBox='0 0 24 24' width='14' xmlns='http://www.w3.org/2000/svg'><path d='M7 10l5 5 5-5z'/></svg>");
    background-repeat: no-repeat;
    background-position: right 6px center;
    background-size: 14px;
`;

const ButtonContainer = styled.div`
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
`;

const ApplyFilterButton = styled.button`
    display: flex;
    align-items: center;
    justify-content: center;
    width: 110px;
    height: 40px;
    background-color: #FDFCFB;
    color: #705C61;
    margin-top: 6px;
    border: 1px solid rgb(204, 199, 195);
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;

    &:hover {
        color: #ffffff;
        background-color: #996932;
        transition: background-color 0.2s;
    }
`;

const ClearFilterButton = styled.button`
    display: flex;
    align-items: center;
    justify-content: center;
    width: 110px;
    height: 40px;
    background-color: #FDFCFB;
    color: #705C61;
    margin-top: 6px;
    border: 1px solid rgb(204, 199, 195);
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;

    &:hover {
        color: #ffffff;
        background-color: #996932;
        transition: background-color 0.2s;
    }
`;

type FilterWindowProps = {
    callback: (
        filters: Array<[string, string, string]>,
        count: Record<string, number>
      ) => void;
    onClose: () => void;
    filters: Array<[string, string, string]>;
    setFilters: React.Dispatch<React.SetStateAction<Array<[string, string, string]>>>;
    filterCount: Record<string, number>;
    setFilterCount: React.Dispatch<React.SetStateAction<Record<string, number>>>;
    selectedOptions: Record<string, Set<any>>;
    setSelectedOptions: React.Dispatch<React.SetStateAction<Record<string, Set<any>>>>;
    maxPrice: number;
    minPrice: number;
};

const FilterWindow = ({ callback, onClose, filters, setFilters, filterCount, setFilterCount, selectedOptions, setSelectedOptions, maxPrice, minPrice }: FilterWindowProps) => {
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

    const [activeFilter, setActiveFilter] = useState<string | null>(null);
    const [filterPosition, setFilterPosition] = useState<{ top: number, left: number }>({ top: 0, left: 0 });
    const [auctionBeforeDate, setAuctionBeforeDate] = useState<Dayjs | null>(null);
    const [auctionAfterDate, setAuctionAfterDate] = useState<Dayjs | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const optionsRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as Node;

            if (containerRef.current &&
                !containerRef.current.contains(target) &&
                (!optionsRef.current || !optionsRef.current.contains(target))
            ) {
                onClose();
            }
        };
        
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [onClose]);

    useEffect(() => {
        if (typeof window !== "undefined") {
            const now = dayjs();
            setAuctionBeforeDate(now);
            setAuctionAfterDate(now);
        }
      }, []);

    const handleAddFilter = (filter: string, value: string) => {
        const filterKey = keyMap[filter];
        const newFilters = toggleFilter(filters, filterKey, "eq", value);

        const existed = filters.length > newFilters.length;

        setFilters(newFilters);
        setFilterCount((prevCount) => ({
            ...prevCount,
            [filter]: prevCount[filter] + (existed ? -1 : 1),
        }));

        setSelectedOptions((prevSelected) => {
            const currentSet = new Set(prevSelected[filter] || []);
            if (currentSet.has(value)) {
                currentSet.delete(value);
            } else {
                currentSet.add(value);
            }
            return {
                ...prevSelected,
                [filter]: currentSet,
            };
        });
    };

    const handleAddDateFilter = (filter: string, operator: string, value: Dayjs) => {
        const dateValue = value.format("YYYY-MM-DD");
        const filterKey = keyMap[filter];
        const newFilters = toggleDateFilter(filters, filterKey, operator, dateValue);

        const existed = filters.length > newFilters.length;

        setFilters(newFilters);
        setFilterCount((prevCount) => ({
            ...prevCount,
            [filter]: existed ? 0 : 1,
        }));
    }

    const handleAddYearFilter = (filter: string, operator: string, value: Dayjs) => {
        const yearValue = value.format("YYYY")
        const filterKey = keyMap[filter];
        const newFilters = toggleFilter(filters, filterKey, operator, yearValue);

        const existed = filters.length > newFilters.length;

        setFilters(newFilters);
        setFilterCount((prevCount) => ({
            ...prevCount,
            [filter]: prevCount[filter] + (existed ? -1 : 1),
        }));

        setSelectedOptions((prevSelected) => {
            const currentSet = new Set(prevSelected[filter] || []);
            if (currentSet.has(yearValue)) {
                currentSet.delete(yearValue);
            } else {
                currentSet.add(yearValue);
            }
            return {
                ...prevSelected,
                [filter]: currentSet,
            };
        });
        console.log("selectedOptions", selectedOptions)
    }

    const handleAddPriceRangeFilter = (filter: string, operator: string, minPrice: number, maxPrice: number) => {
        const filterKey = keyMap[filter];
        const newFilters = togglePriceRangeFilter(filters, filterKey, operator, [minPrice, maxPrice]);

        const existed = filters.length > newFilters.length;

        setFilters(newFilters);
        setFilterCount((prevCount) => ({
            ...prevCount,
            [filter]: prevCount[filter] + (existed ? -1 : 1),
        }));
    }

    
    const handleClearFilters = () => {
        const clearedFilters = [] as [string, string, string][];
        const clearedCount = selectFilters.reduce((acc, f) => ({ ...acc, [f]: 0 }), {});
        setFilters(clearedFilters);
        setFilterCount(clearedCount);
        setSelectedOptions({});
        callback(clearedFilters, clearedCount);
    };

    const handleApplyFilters = () => {
        onClose();
        callback(filters, filterCount);
    };

    const handleFilterClick = (filter: string, e: React.MouseEvent<HTMLButtonElement>) => {
        if (typeof window === 'undefined') return;
        const rect = e.currentTarget.getBoundingClientRect();

        if (activeFilter === filter) {
            setActiveFilter(null);
            return;
        } else {
            setActiveFilter(filter);
        }
        setFilterPosition({
            top: rect.bottom + window.scrollY - 35,
            left: rect.right + 10, 
        });
    };

    return (
        <>
            <FilterWindowContainer ref={containerRef}>
                {selectFilters.map((filter, index) => (
                    <SelectFilter key={index} onClick={(e) => handleFilterClick(filter, e)}>
                        {`Select ${filter}`}
                        {filterCount[filter] > 0 && <Count count={filterCount[filter]} />}
                    </SelectFilter>
                ))}

                <ButtonContainer>
                    <ApplyFilterButton onClick={handleApplyFilters}>Apply Filter</ApplyFilterButton>
                    <ClearFilterButton onClick={handleClearFilters}>Clear Filter</ClearFilterButton>
                </ButtonContainer>
            </FilterWindowContainer>

            {activeFilter && (
                <div ref={optionsRef}>
                {(activeFilter === "Auction House" ||
                  activeFilter === "Lot Producer" ||
                  activeFilter === "Region" || 
                  activeFilter === "Colour" || 
                  activeFilter === "Format"
                ) && 
                    <FilterOptions 
                        filterType={activeFilter}
                        position={filterPosition}
                        selected={selectedOptions[activeFilter] || new Set()}
                        onClick={(value) => handleAddFilter(activeFilter, value)}
                        onClose={() => setActiveFilter(null)}
                    />
                }
                {activeFilter === "Vintage" && (
                    <CustomYearCalendar 
                        position={filterPosition}
                        selected={selectedOptions[activeFilter] || new Set()}
                        callback={(value) => handleAddYearFilter(activeFilter, "eq", value)}
                    />
                )}
                {(activeFilter === "Auction Before" ) && (
                    <FullCalendar 
                        position={filterPosition} 
                        initialDate={auctionBeforeDate} 
                        callback={(value) => handleAddDateFilter(activeFilter, "lte", value)}
                        onClose={() => setActiveFilter(null)}
                        setDate={(value) => setAuctionBeforeDate(value)}
                    />
                )}
                {(activeFilter === "Auction After" ) && (
                    <FullCalendar 
                        position={filterPosition} 
                        initialDate={auctionAfterDate} 
                        callback={(value) => handleAddDateFilter(activeFilter, "gte", value)}
                        onClose={() => setActiveFilter(null)}
                        setDate={(value) => setAuctionAfterDate(value)}
                    />
                )}
                {activeFilter === "Price Range" && (
                    <PriceRange 
                        position={filterPosition} 
                        minPrice={minPrice} 
                        maxPrice={maxPrice}
                        onPriceChange={(minPrice, maxPrice) => handleAddPriceRangeFilter(activeFilter, "between", minPrice, maxPrice)}
                    />
                )}
                </div>
            )}
        </>
    );
}

export default FilterWindow;