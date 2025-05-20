import React from "react";
import styled from "styled-components";

const InfoCardContainer = styled.div`
    display: flex;
    flex: 1;
    flex-direction: column;
    align-items: flex-start;
    padding: 25px 28px;
    border: 1px solid #DED9D3;
    border-radius: 10px;
    background-color: #FBF7F4;
    gap: 10px;

`;

const Title = styled.h1`
    font-size: 20px;
    color: #542a35;
    margin: 0;
`;

const Description = styled.p`
    font-size: 13px;
    color:rgba(112, 92, 97, 0.73);
    margin: 0;
`;

const Info = styled.h1`
    font-size: 25px;
    color: #542a35;
    margin: 0;
`;

interface InfoCardProps {
    title: string;
    description: string;
    info: string;
    infoDescription: string;
}

const InfoCard: React.FC<InfoCardProps> = ({ title, description, info, infoDescription}) => {
    return (
        <InfoCardContainer>
            <Title>{title}</Title>
            <Description>{description}</Description>
            <Info>{info}</Info>
            <Description>{infoDescription}</Description>
        </InfoCardContainer>
    );
}

export default InfoCard;