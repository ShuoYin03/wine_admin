import React, { useState, useEffect } from "react";
import styled from "styled-components";
import SquareButton from "../SquareButton/SquareButton";
import ArrowUpShort from "@/assets/arrow-up-short.svg";
import ArrowDownShort from "@/assets/arrow-down-short.svg";

const SortWrapper = styled.div`
    display: flex;
    align-items: center;
    margin-left: 20px;
    margin-right: 10px;
`;

const SortText = styled.span`
    font-size: 13px;
    font-weight: 600;
    color: #705C61;
    margin-right: 5px;
`;

const SortSelect = styled.select`
    width: 160px;
    height: 40px;
    border: 1px solid rgb(204, 199, 195);
    border-radius: 8px;
    background-color: #FDFCFB;
    color: #705C61;
    cursor: pointer;
    margin-right: 10px;
    outline: none;
    padding: 10px;

    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;

    background-image: url("data:image/svg+xml;utf8,<svg fill='%23705C61' height='14' viewBox='0 0 24 24' width='14' xmlns='http://www.w3.org/2000/svg'><path d='M7 10l5 5 5-5z'/></svg>");
    background-repeat: no-repeat;
    background-position: right 6px center;
    background-size: 14px;
`;

type SorterProps = {
    options: { [key: string]: string };
    callback: (orderBy: string) => void;
};

const Sorter = ({
    options,
    callback,
}: SorterProps) => {
    const [sortField, setSortField] = useState("");
    const [sortDirection, setSortDirection] = useState("asc");

    const handleSortDirectionChange = () => {
        setSortDirection((prevDirection) => (prevDirection === "asc" ? "desc" : "asc"));
    }

    useEffect(() => {
        const sortDirectionSymbol = sortDirection === "asc" ? "" : "-";
        callback(`${sortDirectionSymbol}${sortField}`);
    }, [sortField, sortDirection]);

    return (
        <SortWrapper>
            <SortText>Sort by :</SortText>
            <SortSelect onChange={(e) => setSortField(e.target.value)}>
                {Object.entries(options).map(([key, value]) => (
                    <option key={key} value={key}>
                        {value}
                    </option>
                ))}
            </SortSelect>
            <SquareButton onClick={handleSortDirectionChange}>
                {sortDirection === "asc" ? (
                    <ArrowUpShort />
                ) : (
                    <ArrowDownShort />
                )}
            </SquareButton>
        </SortWrapper>
    );
}

export default Sorter;