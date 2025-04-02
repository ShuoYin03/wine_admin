import React from "react";
import styled from "styled-components";

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

const OptionItem = styled.div`
  padding: 5px 10px;
  color: #705c61;
  cursor: pointer;

  &:hover {
    background-color: #f0eae6;
  }
`;

type FilterOptionsProps = {
  filterType: string;
  position: { top: number; left: number };
  onClick: (filter: string) => void;
  onClose: () => void;
};

const dummyOptions: Record<string, string[]> = {
  "Auction House": ["Sotheby's"],
  "Lot Producer": ["Producer A", "Producer B"],
  "Region": ["France", "Italy", "USA"],
  "Colour": ["Red", "White", "Rosé"],
  "Format": ["750ml", "1.5L", "3L"],
  "Vintage": ["2010", "2015", "2020"],
  "Auction Before": ["2024-01-01", "2023-01-01"],
  "Auction After": ["2022-01-01", "2021-01-01"],
};

const FilterOptions: React.FC<FilterOptionsProps> = ({ filterType, position, onClick, onClose }: FilterOptionsProps) => {
  const options = dummyOptions[filterType] || [];

  return (
    <OptionsContainer top={position.top} left={position.left}>
      {options.map((opt, i) => (
        <OptionItem key={i} onClick={() => {
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
