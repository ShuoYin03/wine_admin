import React from "react";
import styled from "styled-components";
import Calendar from "@/assets/calendar.svg";

const HomeTitle = styled.h1`
    font-size: 2rem;
    color: #722F37;
    height: 10px;
    padding-top: 20px;
`;

const HomeSubtitleContainer = styled.div`
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 5px;
`;

const AuctionHouse = styled.p`
    font-size: 15px;
    color: #705C61;
    font-weight: bold;
`;

const StyledCalendar = styled(Calendar)`
    position: relative;
    top: 3px;
    width: 16px;
    height: 16px;
    margin-right: 5px;
    fill: #705C61;
`;

const Detail = styled.p`
    font-size: 15px;
    color: #705C61;
`;

const AuctionType = styled.div`
    position: relative;
    top: 1px;
    height: 15px;
    border-radius: 5px;
    font-size: 12px;
    color: #705C61;
    background-color: #F2E6E6;
    font-weight: bold;
    padding: 4px 10px;
    text-align: center;
    text-transform: uppercase;
`;

const Dot = styled.span`
    margin: 0 5px;
    color: #705C61;
`;

interface DetailedMainTitleProps {
    title: string;
    auction_house: string;
    region: string;
    country: string;
    start_date: string;
    end_date: string;
    auction_type: string;
}

const DetailedMainTitle: React.FC<DetailedMainTitleProps> = ({ title, auction_house, region, country, start_date, end_date, auction_type }) => {
    return (
        <>
            <HomeTitle>{title}</HomeTitle>
            <HomeSubtitleContainer>
                <AuctionHouse>{auction_house}</AuctionHouse>
                <Dot>•</Dot>
                <Detail>{region}, {country}</Detail>
                <Dot>•</Dot>
                <Detail>
                    <StyledCalendar />
                    {start_date} - {end_date}
                </Detail>
                <Dot>•</Dot>
                <AuctionType>{auction_type}</AuctionType>
            </HomeSubtitleContainer>
        </>
    );
}

export default DetailedMainTitle;