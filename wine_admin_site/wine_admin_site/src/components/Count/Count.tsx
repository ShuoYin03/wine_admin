import React from "react";
import styled from "styled-components";

type CountProps = {
    count: number;
};

const CountContainer = styled.div`
    position: absolute;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    right: 25px;
    height: 13px;
    font-size: 11px;
    font-weight: 600;
    color: #ffffff;
    background-color: #705C61;
    border-radius: 8px;
`;

const Count: React.FC<CountProps> = ({ count }) => {
    return (
        <CountContainer>
            {count}
        </CountContainer>
    );
}

export default Count;