import React from 'react';
import styled from 'styled-components';
import Link from 'next/link';

const Navbar = styled.div`
    display: flex;
    width: 100hr;
    height: 70px;
    align-items: center;
    justify-content: flex-end;
    border-bottom: 1px solid rgb(204, 199, 195);
    padding: 0px 200px;
    background-color: #FEFAF9;
`;

const MainTitle = styled.div`
    display: flex;
    flex: 1;
    justify-self: flex-start;
    font-weight: 600;
    color: #722F37;

    & a {
        display: flex;
        align-items: center;
        text-decoration: none;
        color: #722F37;
        font-size: 17px;
        height: 30px;
    }
`;

const LinkStyled = styled.div`
    display: flex;
    padding: 0px 25px;
    border-radius: 5px;
    
    & a {
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: none;
        color: #722F37;
        font-size: 14px;
        font-weight: 600;
        height: 40px;
    }

    &:hover {
        & a {
            color: #ffffff;
        }
        background-color: #996932;
        transition: background-color 0.2s, color 0.2s;
    }
`;

const Header: React.FC = () => {
    return (
        <Navbar>
            <MainTitle>
                <Link href="/" passHref>Wine Admin</Link>
            </MainTitle>
            <LinkStyled><Link href="/" passHref>Lots</Link></LinkStyled>
            <LinkStyled><Link href="lwinMatching" passHref>Lwin Matching</Link></LinkStyled>
            <LinkStyled><Link href="fxRates" passHref>FX Rates</Link></LinkStyled>
        </Navbar>
    );
};

export default Header;