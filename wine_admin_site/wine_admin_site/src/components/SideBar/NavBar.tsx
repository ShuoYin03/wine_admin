import React from 'react';
import styled from 'styled-components';
import Link from 'next/link';

const Navbar = styled.div`
    display: flex;
    width: 100%;
    height: 70px;
    background-color:rgb(124, 18, 18);
    align-items: center;
    justify-content: center;
`;

const LinkStyled = styled.div`
    display: flex;
    padding: 0px 30px;

    & a {
        display: flex;
        align-items: center;
        text-decoration: none;
        color: #ffffff;
        font-size: 17px;
        height: 70px;
    }

    &:hover {
        background-color:rgb(223, 34, 34);
        color: black;
    }
`;

const NavBar: React.FC = () => {
    return (
        <Navbar>
            <LinkStyled><Link href="/" passHref>Home</Link></LinkStyled>
            <LinkStyled><Link href="lots" passHref>Lots</Link></LinkStyled>
            <LinkStyled><Link href="lwin-matching" passHref>Lwin Matching</Link></LinkStyled>
            <LinkStyled><Link href="fx-rates" passHref>FX Rates</Link></LinkStyled>
        </Navbar>
    );
};

export default NavBar;