'use client';
import React from 'react';
import MainTitle from '@/components/MainTitle/MainTitle';
import Container from '@/components/Container/Container';

const Home = () => {
    return (
      <Container>
        <MainTitle title={"Wine Admin Site"} subtitle={"Browse, Search, and Manage Wine Lots"}></MainTitle>
      </Container>
    );
}

export default Home;