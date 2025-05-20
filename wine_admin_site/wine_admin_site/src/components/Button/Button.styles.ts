// components/Buttons/Button.styles.ts
import styled, { css } from 'styled-components';
import { ButtonMode } from './Button.types';

export const baseButtonStyles = css<{ mode?: ButtonMode }>`
    width: 110px;
    height: 40px;
    padding: 0 16px;
    font-weight: 600;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.2s, color 0.2s;

    ${({ mode }) => {
        switch (mode) {
        case 'primary':
            return css`
            background-color: #722F37;
            color: white;
            border: none;

            &:hover {
                background-color: #4E1F25;
            }
            `;
        case 'outline':
            return css`
            background-color: #FDFCFB;
            color: #705C61;
            border: 1px solid #ccc;

            &:hover {
                background-color: #996932;
                color: white;
            }
            `;
        case 'dashed':
            return css`
            background-color: #FDFCFB;
            color: #705C61;
            border: 1px dashed #705C61;

            &:hover {
                background-color: #996932;
                color: white;
            }
            `;
        case 'ghost':
            return css`
            background: transparent;
            border: none;
            color: inherit;
            `;
        default:
            return '';
        }
    }}
`;

export const StyledButton = styled.button<{ mode?: ButtonMode }>`
  ${baseButtonStyles}
  display: flex;
  align-items: center;
  justify-content: center;
`;
