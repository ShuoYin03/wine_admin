import React from "react";
import styled from "styled-components";

const HomeTitle = styled.h1`
    font-size: 2rem;
    color: #722F37;
    height: 10px;
    padding-top: 20px;
`;

const HomeSubtitle = styled.p`
    font-size: 15px;
    color: #705C61;
    margin-bottom: 40px;
`;

interface MainTitleProps {
    title: string;
    subtitle: string;
}

const MainTitle: React.FC<MainTitleProps> = ({ title, subtitle }) => {
    return (
        <>
            <HomeTitle>{title}</HomeTitle>
            <HomeSubtitle>{subtitle}</HomeSubtitle>
        </>
    );
}

export default MainTitle;