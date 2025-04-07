import React from "react";
import styled from "styled-components";

const SwitchFilterContainer = styled.div`
    display: flex;
    width: 398px;
    height: 35px;
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    padding: 4px;
    margin: 20px 0px;
    background-color: #EFEBE7;
    gap: 4px;
    border-radius: 8px;
`;

const SwitchOption = styled.div`
    display: flex;
    flex: 1;
    align-items: center;
    justify-content: center;
    height: 100%;
    cursor: pointer;
    background-color: #EFEBE7;
    font-size: 13px;
    font-weight: bold;
    color: #91757A;
    border-radius: 8px;
`

interface SwitchFilterProps {
    options: string[];
    selectedOption: string;
    onSelect: (option: string) => void;
}

const SwitchFilter: React.FC<SwitchFilterProps> = ({ options, selectedOption, onSelect }) => {
    return (
        <SwitchFilterContainer>
            {options.map((option) => (
                <SwitchOption
                    key={option}
                    onClick={() => onSelect(option)}
                    style={{ backgroundColor: selectedOption === option ? "#FDFCFB" : "#EFEBE7" }}
                >{option}</SwitchOption>
            ))}
        </SwitchFilterContainer>
    )
}

export default SwitchFilter;