import React, { useState, useEffect } from "react";
import styled from "styled-components";
import { 
  keyMap,
  keyMapOptions
 } from "@/utils/staticData"
 import SearchIcon from "@/assets/search.svg";

const FilterOptionsContainer = styled.div<{ top: number; left: number }>`
  position: absolute;
  top: ${({ top }) => top}px;
  left: ${({ left }) => left}px;
  background-color: #ffffff;
  border: 1px solid #ccc;
  border-radius: 6px;
  z-index: 1100;
  width: 220px;
  max-height: 300px;
  overflow-y: overlay;
  overflow-x: hidden;

  &::-webkit-scrollbar {
    width: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background-color: rgba(0, 0, 0, 0.3);
    border-radius: 6px;
  }
`;

const SearchWrapper = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px 8px;
  border-bottom: 1px solid #ccc;
  border-radius: 6px 6px 0px 0px;
`;

const SearchIconWrapper = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 8px;
  padding-left: 10px;

  svg {
      width: 15px;
      height: 15px;
      fill: #705C61;
  }
`;

const OptionSearchBar = styled.input`
  outline: none;
  border: none;
`;

const OptionsContainer = styled.div`
  padding: 10px;
`;

const OptionContainer = styled.div`
  display: flex;
  padding: 5px 10px;
  align-items: center;
  justify-content: space-between;
`;

const OptionItem = styled.div`
  color: #705c61;
  cursor: pointer;
`;

const OptionTickBox = styled.input`
  display: block;
  height: 16px;
  width: 16px;
  accent-color: #996932;
  cursor: pointer;
`;

type FilterOptionsProps = {
  filterType: string;
  position: { top: number; left: number };
  selected: Set<string>;
  onClick: (filter: string) => void;
  onClose: () => void;
};

const FilterOptions: React.FC<FilterOptionsProps> = ({ filterType, position, selected, onClick, onClose }: FilterOptionsProps) => {
  const [options, setOptions] = useState<string[]>([]);
  const [displayOptions, setDisplayOptions] = useState<string[]>([]);
  
  useEffect(() => {
    const keyMapFilter = keyMap[filterType] || filterType;
    const keyMapOptionsList = keyMapOptions[keyMapFilter] || [];
    setOptions(keyMapOptionsList);
    setDisplayOptions(keyMapOptionsList);
  }, [filterType]);

  return (
    <FilterOptionsContainer top={position.top} left={position.left}>
      <SearchWrapper>
        <SearchIconWrapper>
          <SearchIcon />
        </SearchIconWrapper>
        <OptionSearchBar 
            type="text" 
            placeholder="Search..." 
            onChange={(e) => {
              const searchTerm = e.target.value.toLowerCase();
              const filteredOptions = options.filter(option => option.toLowerCase().includes(searchTerm));
              setDisplayOptions(filteredOptions);
            }}
          />
      </SearchWrapper>
      <OptionsContainer>
        {displayOptions.map((opt, i) => (
          <OptionContainer key={i} onClick={() => onClick(opt)}>
            <OptionItem >
              {opt}
            </OptionItem>
            <OptionTickBox 
              type="checkbox"
              checked={selected.has(opt)}
              onClick={(e) => {
                e.stopPropagation();
                onClick(opt);  
              }}
              readOnly
            />
          </OptionContainer>
        ))}
      </OptionsContainer>
    </FilterOptionsContainer>
  );
};

export default FilterOptions;
