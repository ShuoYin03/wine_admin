import styled from 'styled-components';

export const DefaultContainer = styled.div`
  display: flex;
  flex-direction: column;
  background-color: #FDF8F5;
  padding: 0 160px;
  min-height: 82vh;
  padding-bottom: 160px; 
`;

export const CenteredContainer = styled.div`
  display: flex;
  flex-direction: column;
  background-color: #FDF8F5;
  padding: 40px;
  max-width: 1000px;
  margin: 0 auto;
  min-height: 82vh;
`;

export const FullWidthContainer = styled.div`
  display: flex;
  flex-direction: column;
  background-color: #FDF8F5;
  padding: 0;
  width: 100%;
`;

export const BoxedContainer = styled.div`
  display: flex;
  flex-direction: column;
  background-color: white;
  padding: 30px;
  max-width: 900px;
  margin: 40px auto;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  border-radius: 12px;
  min-height: 82vh;
`;

export const CompactContainer = styled.div`
  display: flex;
  flex-direction: column;
  padding: 20px 40px;
  background-color: #FDF8F5;
  min-height: 82vh;
  
`;

export type ContainerMode = 'default' | 'centered' | 'fullWidth' | 'boxed' | 'compact';
