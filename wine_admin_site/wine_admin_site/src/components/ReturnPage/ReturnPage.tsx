'use client';
import React from "react";
import styled from "styled-components";
import { useRouter } from "next/navigation";
import ArrowLeft from "@/assets/arrow-left.svg";

const ReturnPageContainer = styled.div`
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    position: relative;
    top: 20px;
`;

const ReturnText = styled.p`
    font-size: 16px;
    color: #705C61;
    font-weight: bold;
    cursor: pointer;
    &:hover {
        transition: 0.3s;
        transform: translateY(1px);
    }

    &:active {
        transition: 0.3s;
        transform: translateY(2px);
    }
`;

const ArrowLeftIcon = styled(ArrowLeft)`
    position: relative;
    top: 2px;
    width: 16px;
    height: 16px;
    margin-right: 5px;
`;

interface ReturnPageProps {
    text: string;
}

const ReturnPage: React.FC<ReturnPageProps> = ({ text }) => {
    const router = useRouter();

    const handleClick = () => {
        router.back();
    };

    return (
        <ReturnPageContainer>
            <ReturnText onClick={handleClick}>
                <ArrowLeftIcon />  Back To {text}
            </ReturnText>
        </ReturnPageContainer>
    )
}

export default ReturnPage;