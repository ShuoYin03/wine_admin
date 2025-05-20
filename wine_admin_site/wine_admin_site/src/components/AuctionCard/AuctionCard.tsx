import React from 'react';
import {
  CardContainer,
  Tag,
  SoldBadge,
  Title,
  SubText,
  InfoRow,
  CalendarIcon,
  Label,
  Amount,
  Button,
  ButtonWrapper,
  FlexRow
} from './AuctionCard.styles';
import { AuctionType } from '@/types/auctionApi';
import getCurrencySymbol from '@/utils/getCurrencySymbol';
import formatAmount from '@/utils/amountFormat';

type AuctionCardProps = {
    auction: AuctionType;
    onClick?: () => void;
};

const AuctionCard: React.FC<AuctionCardProps> = ({
    auction,
    onClick
}) => {
  return (
    <CardContainer>
        <FlexRow style={{ justifyContent: 'space-between' }}>
            {auction.auction_type == "LIVE" && <Tag>Live</Tag>}
            {auction.auction_type == "PAST" && <Tag>PAST</Tag>}
            <SoldBadge>{auction.sales?.sold} / {auction.sales?.lots} Sold</SoldBadge>
        </FlexRow>

        <Title>{auction.auction_title}</Title>
        <SubText>{auction.auction_house}</SubText>

        <InfoRow>
            <CalendarIcon />
            <span>{auction.start_date?.toLocaleString()}</span>
            <span>{auction.city}</span>
        </InfoRow>

        <Label>Total Sales</Label>
        <Amount>{getCurrencySymbol(auction.sales?.currency)}{formatAmount(auction.sales?.total_sales)}</Amount>

        <ButtonWrapper>
            <Button onClick={onClick}>
                View Auction →
            </Button>
        </ButtonWrapper>
    </CardContainer>
  );
};

export default AuctionCard;
