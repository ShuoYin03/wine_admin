import React from "react";
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
`;

interface PriceRangeProps {
    position : { top: number; left: number };
    onPriceChange?: (minPrice: number, maxPrice: number) => void;
}

const PriceRange: React.FC<PriceRangeProps> = ({ position, onPriceChange }) => {
    return (
        <PriceRangeContainer top={position.top} left={position.left}>

        </PriceRangeContainer>
    )
}

export default PriceRange;