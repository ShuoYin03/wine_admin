import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import dayjs, { Dayjs } from 'dayjs';

const Container = styled.div<{ top: number; left: number }>`
  position: absolute;
  top: ${({ top }) => top}px;
  left: ${({ left }) => left}px;
  max-height: 300px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 20px;
  background-color: #ffffff;
  border: 1px solid #ccc;
  border-radius: 8px;
  width: 300px;
  z-index: 1100;
  overflow: auto;

  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
`;

const YearButton = styled.button<{ selected: boolean }>`
  width: 80px;
  height: 35px;
  border-radius: 8px;
  border: 1px solid #ccc;
  background-color: ${({ selected }) => (selected ? '#996932' : '#F5F5F5')};
  color: ${({ selected }) => (selected ? '#ffffff' : '#333')};
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;

  &:hover {
    background-color: ${({ selected }) => (selected ? '#996932' : '#e0e0e0')};
  }
`;

interface CustomYearSelectorProps {
  position: { top: number; left: number };
  selected: Set<string>;
  callback: (year: Dayjs) => void;
}

const CustomYearSelector: React.FC<CustomYearSelectorProps> = ({
  position,
  selected,
  callback,
}) => {
  const [selectedYears, setSelectedYears] = useState<Set<string>>(new Set(selected));
  const [years, setYears] = useState<string[]>([]);

  const toggleYear = (year: string) => {
    const newSelected = new Set(selectedYears);
    if (newSelected.has(year)) {
      newSelected.delete(year);
    } else {
      newSelected.add(year);
    }
    setSelectedYears(newSelected);
    callback(dayjs(year, 'YYYY'));
  };

  useEffect(() => {
    const currentYear = dayjs().year();
    const generatedYears = [];
    for (let y = 1900; y <= currentYear; y++) {
      generatedYears.push(y.toString());
    }
    setYears(generatedYears);
  }, []);

  return (
    <Container top={position.top} left={position.left}>
      {years.map((year) => (
        <YearButton
          key={year}
          selected={selectedYears.has(year)}
          onClick={() => toggleYear(year)}
        >
          {year}
        </YearButton>
      ))}
    </Container>
  );
};

export default CustomYearSelector;