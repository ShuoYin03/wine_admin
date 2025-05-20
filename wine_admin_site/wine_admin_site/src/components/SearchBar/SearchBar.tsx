import React, { useState, useRef } from "react";
import styled from "styled-components";
import FunnelIcon from "@/assets/funnel.svg";
import FilterWindow from "./FilterWindow";
import Button from "../Button/Button";
import Container from "../Container/Container";
import Sorter from "../Sorter/Sorter";
import { useFilterContext } from "@/contexts/FilterContext";
import Search from "../Search/Search";
import { Download } from "lucide-react";

const SearchBarContainer = styled.div`
    display: flex;
    align-items: center;
    width: 100%;
    height: 45px;
    gap: 10px;
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
    height: 40px;
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

interface SearchBarProps {
    exportCallback?: () => void;
    type: string;
};

const SearchBar: React.FC<SearchBarProps> = ({ 
    exportCallback,
    type
}) => {
    const [showFilterWindow, setShowFilterWindow] = useState(false);
    const [filterWindowPosition, setFilterWindowPosition] = useState<{ top: number, left: number }>({ top: 0, left: 0 });
    const [searchText, setSearchText] = useState("");
    const filterButtonRef = useRef<HTMLButtonElement>(null);
    
    const {
        filters,
        setFilters,
        setOrderBy,
        setFilterCount,
        orderByOptions,
      } = useFilterContext();
    

    const toggleFilterWindow = () => {
        if (filterButtonRef.current) {
          const rect = filterButtonRef.current.getBoundingClientRect();
          setFilterWindowPosition({
            top: rect.bottom + window.scrollY - 45,
            left: rect.left + window.scrollX
          });
        }
        setShowFilterWindow(!showFilterWindow);
      };
    
    const handleSubmit = () => {
        let searchField = "";
        if (type === "lot") {
            searchField = "wine_name";
        } else if (type === "auction") {
            searchField = "auction_title";
        }

        const cleanedFilters = filters.filter(
            ([field, operator]) => operator !== "like"
        );

        const newFilters: [string, string, string][] = [
            ...cleanedFilters,
            [searchField, "like", searchText]
        ];

        setFilters(newFilters);
    };

    const handleFilterChange = (
        filters: Array<[string, string, string]>, 
        count: Record<string, number>
    ) => {
        setFilters(filters);
        setFilterCount(count);
    };

    return (
        <Container mode="fullWidth">
            <SearchBarContainer>
                <Search setSearchText={setSearchText} handleSubmit={handleSubmit}/>
                <Button onClick={handleSubmit}>Search</Button>
                <RightSideContainer>
                    <FilterButton 
                        ref={filterButtonRef}
                        onMouseDown={(e) => {e.stopPropagation(); toggleFilterWindow();
                    }}>
                        <FilterIconWrapper>
                            <FunnelIcon />
                        </FilterIconWrapper>
                        <FilterText>Filters</FilterText>
                    </FilterButton>
                    <Sorter options={orderByOptions} callback={setOrderBy} />
                    <Button mode="outline" onClick={exportCallback}>
                        <Download size={16} style={{"marginRight": "5px"}}/>
                        Export
                    </Button>
                </RightSideContainer>
            </SearchBarContainer>
            {showFilterWindow && 
                <FilterWindow 
                    position={filterWindowPosition}
                    callback={handleFilterChange}
                    onClose={() => toggleFilterWindow()}
                    type={type}
                />}
        </Container>
  );
};

export default SearchBar;
