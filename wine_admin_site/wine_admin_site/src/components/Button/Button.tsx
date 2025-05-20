'use client';
import React from 'react';
import { StyledButton } from './Button.styles';
import { ButtonProps } from './Button.types';

const Button: React.FC<ButtonProps> = ({ children, mode = 'primary', ...rest }) => {
  return (
    <StyledButton mode={mode} {...rest}>
      {children}
    </StyledButton>
  );
};

export default Button;
