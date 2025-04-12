import React, { useState, useEffect } from "react";
import styled from "styled-components";
import { 
  keyMap,
  keyMapOptions
 } from "@/utils/data"

const OptionsContainer = styled.div<{ top: number; left: number }>`
  position: absolute;
  top: ${({ top }) => top}px;
  left: ${({ left }) => left}px;
  background-color: #ffffff;
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 10px;
  z-index: 1100;
  width: 180px;
`;

const OptionItem = styled.div<{ $isSelected?: boolean }>`
  padding: 5px 10px;
  color: #705c61;
  cursor: pointer;
  background-color: ${({ $isSelected }) => ($isSelected ? "#f0eae6" : "ffffff")};

  &:hover {
    background-color: #f0eae6;
  }
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
  
  useEffect(() => {
    // const fetchOptions = async () => {
    //   const mappedFilter = keyMap[filterType] || filterType;
    //   const payload = {
    //     select_fields: [mappedFilter],
    //     distinct_fields: mappedFilter,
    //   };

    //   const response = await fetch(`http://localhost:5000/lot_query`, {
    //     method: "POST",
    //     headers: {
    //       "Content-Type": "application/json",
    //     },
    //     body: JSON.stringify(payload),
    //   });
      
    //   const result = await response.json();
    //   const data = await handleResponse(result['lots']);
    //   console.log(data);
    //   setOptions(data);
    // };

    // fetchOptions();
    const keyMapFilter = keyMap[filterType] || filterType;
    const keyMapOptionsList = keyMapOptions[keyMapFilter] || [];
    setOptions(keyMapOptionsList);
  }, [filterType]);

  return (
    <OptionsContainer top={position.top} left={position.left}>
      {options.map((opt, i) => (
        <OptionItem 
          key={i} 
          $isSelected={selected.has(opt)}
          onClick={() => {
            onClick(opt);
            onClose();
        }}>
          {opt}
        </OptionItem>
      ))}
    </OptionsContainer>
  );
};

export default FilterOptions;
