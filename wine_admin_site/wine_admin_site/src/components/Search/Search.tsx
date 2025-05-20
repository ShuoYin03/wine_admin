import React from 'react';
import styled from 'styled-components';
import SearchIcon from "@/assets/search.svg";

const SearchWrapper = styled.div`
    display: flex;
    align-items: center;
    width: 360px;
    height: 40px;
    border: 1px solid #DED9D3;
    border-radius: 10px;
    padding: 0 12px;
    background-color: #FDFCFB;
`;

const SearchIconWrapper = styled.div`
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 5px;
    padding-top: 2px;
    padding-left: 2px;

    svg {
        width: 16px;
        height: 16px;
        fill: #705C61;
    }
`;

const SearchInput = styled.input`
    flex: 1;
    height: 100%;
    border: none;
    font-size: 14px;
    outline: none;
    background-color: transparent;
    color: #333;

    &::placeholder {
        color: #705C61;
    }
`;

type SearchProps = {
    setSearchText: (text: string) => void;
    handleSubmit: () => void;
};

const Search: React.FC<SearchProps> = ({ setSearchText, handleSubmit}) => {
    return (
        <SearchWrapper>
            <SearchIconWrapper>
            <SearchIcon />
            </SearchIconWrapper>
            <SearchInput 
                placeholder="Search lots by name, vintage, region..." 
                onChange={(e) => setSearchText(e.target.value)} 
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        handleSubmit();
                    }
                }}
            />
        </SearchWrapper>
    );
};

export default Search;