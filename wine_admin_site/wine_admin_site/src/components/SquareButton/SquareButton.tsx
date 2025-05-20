import React from "react";
import styled from "styled-components";

type SquareButtonProps = {
    onClick: () => void;
    children?: React.ReactNode;
};

const SquareButtonContainer = styled.button`
    display: flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    background-color: #FEFAF9;
    border: 1px solid rgb(204, 199, 195);
    border-radius: 5px;
    cursor: pointer;
    color: #552B35;
    font-size: 16px;

    &:hover {
        background-color: #996932;
        transition: background-color 0.2s, color 0.2s;

        .svg {
            fill: #ffffff;
        }
    }
`;

const SquareButton = ({ onClick, children }: SquareButtonProps) => {
    return (
        <SquareButtonContainer onClick={onClick}>
            {children}
        </SquareButtonContainer>
    );
}

export default SquareButton;