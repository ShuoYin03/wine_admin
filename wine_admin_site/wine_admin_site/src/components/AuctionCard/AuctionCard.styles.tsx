import styled from 'styled-components';
import { CalendarDays } from 'lucide-react';

export const CardContainer = styled.div`
  background: #fffaf8;
  border: 1px solid #e2ddd9;
  border-radius: 12px;
  padding: 20px;
  width: 289px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
`;

export const Card = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #fff;
`;

export const FlexRow = styled.div`
  display: flex;
  align-items: center;
`;

export const Tag = styled.div`
  background-color: #f3ece9;
  color: #7d5e5b;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 8px;
  font-weight: 500;
`;

export const SoldBadge = styled.div`
  background-color: #7d434c;
  color: #ffffff;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 8px;
  font-weight: 600;
`;

export const Title = styled.h2`
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px 0;
  line-height: 1.3;
  height: 3.6em; // 约等于 3 行
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
`;

export const SubText = styled.p`
  font-size: 14px;
  color: #7d5e5b;
  margin: 0;
`;

export const InfoRow = styled.div`
  display: flex;
  align-items: center;
  font-size: 14px;
  gap: 8px;
  color: #705c61;
`;

export const CalendarIcon = styled(CalendarDays)`
  width: 16px;
  height: 16px;
`;

export const Label = styled.p`
  font-size: 13px;
  color: #705c61;
  margin: 8px 0 0;
`;

export const Amount = styled.p`
  font-size: 20px;
  font-weight: 700;
  color: #5b1f25;
  margin: 0;
`;

export const ButtonWrapper = styled.div`
  margin-top: auto;
  display: flex;
  justify-content: flex-start;
`;

export const Button = styled.button`
  margin-top: 8px;
  width: 100%;
  padding: 10px;
  background-color: #fcf8f6;
  color: #5b1f25;
  border: 1px solid #d4c8c5;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background-color: #7d434c;
    color: #fff;
  }
`;
