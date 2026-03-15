import styled from 'styled-components';
import React from 'react';

const CardGridStyled = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: flex-start;
  padding-top: 20px;
`;

const CardGrid = React.memo(({ children }: { children: React.ReactNode }) => {
    return <CardGridStyled>{children}</CardGridStyled>;
});
CardGrid.displayName = 'CardGrid';

export default CardGrid;