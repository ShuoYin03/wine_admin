'use client';
import React from 'react';
import styled from 'styled-components';
import dayjs, { Dayjs } from 'dayjs';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DateCalendar } from '@mui/x-date-pickers/DateCalendar';

const FullCalendarContainer = styled.div<{ top: number; left: number }>`
  position: absolute;
  top: ${({ top }) => top}px;
  left: ${({ left }) => left}px;
  background-color: #ffffff;
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 10px;
  z-index: 1100;
`;

type FullCalendarProps = {
  position: { top: number; left: number };
  initialDate: Dayjs | null;
  callback: (date: Dayjs) => void;
  onClose: () => void;
  setDate: (date: Dayjs) => void;
};

const FullCalendar: React.FC<FullCalendarProps> = ({ position, initialDate, callback, onClose, setDate }) => {
  return (
    <FullCalendarContainer top={position.top} left={position.left}>
      <LocalizationProvider dateAdapter={AdapterDayjs}>
          <DateCalendar 
            value={initialDate} 
            onChange={(newValue) => {
              callback(newValue)
              setDate(newValue)
              onClose()
            }}/>
      </LocalizationProvider>
    </FullCalendarContainer>
  );
}

export default FullCalendar;