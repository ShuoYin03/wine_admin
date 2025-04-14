import React, { useState } from "react";
import styled from "styled-components";

const PriceRangeContainer = styled.div<{ top: number; left: number }>`
    position: absolute;
    top: ${({ top }) => top}px;
    left: ${({ left }) => left}px;
    background-color: #ffffff;
    border: 1px solid #ccc;
    border-radius: 6px;
    padding: 10px;
    z-index: 1100;
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 220px;
`;

const Label = styled.label`
    font-size: 14px;
    font-weight: 600;
    color: #333;
`;

const Input = styled.input`
    width: 200px;
    padding: 6px 8px;
    margin-top: 4px;
    border: 1px solid #ccc;
    border-radius: 6px;
    font-size: 14px;
    &:focus {
        border-color: #996932;
        outline: none;
    }
`;

const ApplyButton = styled.button`
  margin-top: 10px;
  padding: 8px 12px;
  background-color: #996932;
  color: #ffffff;
  font-weight: bold;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  &:hover {
    background-color: #704f22;
  }
`;

interface PriceRangeProps {
  position: { top: number; left: number };
  maxPrice: number;
  minPrice: number;
  onPriceChange: (minPrice: number, maxPrice: number) => void;
}

const PriceRange: React.FC<PriceRangeProps> = ({
  position,
  minPrice = 0,
  maxPrice = 10000,
  onPriceChange,
}) => {
  const [min, setMin] = useState<number>(minPrice);
  const [max, setMax] = useState<number>(maxPrice);

  const handleApply = () => {
    if (onPriceChange) {
      onPriceChange(min, max);
    }
  };

  return (
    <PriceRangeContainer top={position.top} left={position.left}>
      <div>
        <Label>Min Price</Label>
        <Input
          type="number"
          value={min === 0 ? '' : min}
          onChange={(e) => {
            const val = e.target.value;
            if (val === '') {
              setMin(0);
            } else {
              setMin(Number(val));
        }}}/>
      </div>
      <div>
        <Label>Max Price</Label>
        <Input
          type="number"
          value={min === 0 ? '' : min}
          onChange={(e) => {
            const val = e.target.value;
            if (val === '') {
              setMin(0);
            } else {
              setMin(Number(val));
        }}}/>
      </div>
      <ApplyButton onClick={handleApply}>Add Filter</ApplyButton>
    </PriceRangeContainer>
  );
};

export default PriceRange;
