import React from "react";
import styled from "styled-components";

const FilterWindowContainer = styled.div`
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    width: 230px;
    height: 380px;
    padding: 0px 5px;
    margin-top: 50px;
    margin-left: 687px;
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

const SelectFilter = styled.select`
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

const FilterWindow = () => {
    const selectFilters = [
        "Auction House",
        "Lot Producer",
        "Region",
        "Colour",
        "Format",
        "Vintage",
        "Auction Before",
        "Auction After",
    ];

    return (
        <FilterWindowContainer>
            {selectFilters.map((filter, index) => (
                <SelectFilter key={index}>
                    <option value="">{`Select ${filter}`}</option>
                    <option value="option1">Option 1</option>
                    <option value="option2">Option 2</option>
                </SelectFilter>
            ))}
            {/* {slideFilters.map((filter, index) => (
                <SlideFilterContainer key={index}>
                    <label>{filter}</label>
                    <input type="range" min="0" max="100" />
                </SlideFilterContainer>
            ))} */}
            <ButtonContainer>
                <ApplyFilterButton>Apply Filter</ApplyFilterButton>
                <ClearFilterButton>Clear Filter</ClearFilterButton>
            </ButtonContainer>
        </FilterWindowContainer>
    );
}

export default FilterWindow;