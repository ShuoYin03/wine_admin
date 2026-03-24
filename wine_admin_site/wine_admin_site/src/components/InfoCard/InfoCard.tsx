import React, { useState } from "react";
import styled from "styled-components";

const InfoCardContainer = styled.div`
    display: flex;
    flex: 1;
    min-width: 0;
    flex-direction: column;
    align-items: flex-start;
    padding: 25px 28px;
    border: 1px solid #DED9D3;
    border-radius: 10px;
    background-color: #FBF7F4;
    gap: 10px;
    position: relative;
    overflow: hidden;
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
    width: 100%;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
`;

const Info = styled.h1`
    font-size: 25px;
    color: #542a35;
    margin: 0;
    width: 100%;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
`;

const CopyButton = styled.button<{ $copied: boolean }>`
    position: absolute;
    top: 14px;
    right: 14px;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: ${({ $copied }) => ($copied ? '#2e7d32' : '#705C61')};
    background: transparent;
    border: none;
    cursor: pointer;
    transition: color 0.15s ease;
    &:hover {
        color: ${({ $copied }) => ($copied ? '#2e7d32' : '#3d2428')};
    }
`;

interface InfoCardProps {
    title: string;
    description: string;
    info: string;
    infoDescription: string;
    copyValue?: string;
}

const InfoCard: React.FC<InfoCardProps> = ({ title, description, info, infoDescription, copyValue }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        if (!copyValue) return;
        navigator.clipboard.writeText(copyValue).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    return (
        <InfoCardContainer>
            <Title>{title}</Title>
            <Description>{description}</Description>
            <Info title={info}>{info}</Info>
            <Description>{infoDescription}</Description>
            {copyValue !== undefined && (
                <CopyButton $copied={copied} onClick={handleCopy} title={copied ? 'Copied!' : 'Copy'}>
                    {copied ? (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                        </svg>
                    ) : (
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                        </svg>
                    )}
                </CopyButton>
            )}
        </InfoCardContainer>
    );
}

export default InfoCard;