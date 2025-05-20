import React from 'react';
import {
    DefaultContainer,
    CenteredContainer,
    FullWidthContainer,
    BoxedContainer,
    CompactContainer,
    ContainerMode
} from './Container.style';

type ContainerProps = {
    children: React.ReactNode;
    mode?: ContainerMode;
  };

const Container: React.FC<ContainerProps> = ({ children, mode = 'default' }) => {
    const getContainer = () => {
      switch (mode) {
        case 'centered':
          return CenteredContainer;
        case 'fullWidth':
          return FullWidthContainer;
        case 'boxed':
          return BoxedContainer;
        case 'compact':
          return CompactContainer;
        case 'default':
        default:
          return DefaultContainer;
      }
    };
  
    const SelectedContainer = getContainer();
  
    return (
        <SelectedContainer>{children}</SelectedContainer>
    );
  };
  
export default Container;
