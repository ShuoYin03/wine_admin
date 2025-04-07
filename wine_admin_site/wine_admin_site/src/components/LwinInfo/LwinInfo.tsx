import React from "react";
import styled from "styled-components";

const LwinInfoContainer = styled.div`
    display: flex;
    height: 100px;
    width: 100%;
    gap: 10px;
`;

const LeftContainer = styled.div`
    display: flex;
    flex-direction: column;
    width: 30%;
    border-radius: 8px;
    border: 1px solid #D8BDC0;
    padding: 20px 15px;
`

const TotalLwinTitle = styled.span`
    font-size: 12px;
    font-weight: bold;
    color: #705C61;
    margin-bottom: 10px;
`;

const TotalLwinCount = styled.span`
    font-size: 20px;
    font-weight: bold;
    color: #542A35;
    margin-top: 8px;
`;

const RightContainer = styled.div`
    display: flex;
    width: 70%;
    border-radius: 8px;
    border: 1px solid #D8BDC0;
    padding: 20px 15px;
`;

const StausInfoContainer = styled.div`
    display: flex;
    flex: 1;
    height: 100%;
    flex-direction: column;
`;

const StatusInfoTitle = styled.span`
    font-size: 12px;
    font-weight: bold;
    color: #705C61;
    margin-bottom: 10px;
`;

const StatusCount = styled.span`
    font-size: 20px;
    font-weight: bold;
    color: #542A35;
    margin-top: 8px;
`;

interface LwinInfoProps {
    totalLwinCount: number;
    exactMatchCount: number;
    multiMatchCount: number;
    noMatchCount: number;
}

const LwinInfo: React.FC<LwinInfoProps> = ({ totalLwinCount, exactMatchCount, multiMatchCount, noMatchCount }) => {
    return (
        <LwinInfoContainer>
            <LeftContainer>
                <TotalLwinTitle>Total LWIN Count: </TotalLwinTitle>
                <TotalLwinCount>{totalLwinCount}</TotalLwinCount>
            </LeftContainer>
            <RightContainer>
                <StausInfoContainer>
                    <StatusInfoTitle>Exact Match Count: </StatusInfoTitle>
                    <StatusCount>{exactMatchCount}</StatusCount>
                </StausInfoContainer>
                <StausInfoContainer>
                    <StatusInfoTitle>Multi Match Count: </StatusInfoTitle>
                    <StatusCount>{multiMatchCount}</StatusCount>
                </StausInfoContainer>
                <StausInfoContainer>
                    <StatusInfoTitle>No Match Count: </StatusInfoTitle>
                    <StatusCount>{noMatchCount}</StatusCount>
                </StausInfoContainer>
            </RightContainer>
        </LwinInfoContainer>
    )
}

export default LwinInfo;