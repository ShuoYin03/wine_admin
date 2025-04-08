import React from "react";
import styled from "styled-components";
import SquareButton from "@/components/SquareButton/SquareButton";
import ChevronLeft from '@/assets/chevron-left.svg';
import ChevronRight from '@/assets/chevron-right.svg';
import ChevronDoubleLeft from '@/assets/chevron-double-left.svg';
import ChevronDoubleRight from '@/assets/chevron-double-right.svg';

const TableBottomContainer = styled.div`
    display: flex;
    width: 100%;
    height: 50px;
    margin-top: 15px;
    align-items: center;
    justify-content: flex-start;
    font-size: 15px;
`;

const DisplayPageSize = styled.div`
    display: flex;
    color: #705C61;
`;

const PageSizeSwitchContainer = styled.div`
    display: flex;
    align-items: center;
    justify-content: center;
    margin-left: 20px;
`;

const PageSizeText = styled.span`
    display: flex;
    color:rgb(90, 74, 78);
    font-weight: 600;
`;

const PageSizeSwitcher = styled.select`
    display: flex;
    margin-left: 20px;
    padding: 10px;
    width: 80px;
    height: 35px;
    color: #705C61;
    border-radius: 8px;
    background-color: ##FEFAF9;
    outline: none;

    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;

    background-image: url("data:image/svg+xml;utf8,<svg fill='%23705C61' height='14' viewBox='0 0 24 24' width='14' xmlns='http://www.w3.org/2000/svg'><path d='M7 10l5 5 5-5z'/></svg>");
    background-repeat: no-repeat;
    background-position: right 6px center;
    background-size: 14px;
`;

const PageSwitchContainer = styled.div`
    display: flex;
    flex: 1;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
`;

const DisplayPage = styled.div`
    color: #705C61;
`;

interface DataTableBottomProps {
    page: number;
    setPage: React.Dispatch<React.SetStateAction<number>>;
    pageSize: number;
    setPageSize: React.Dispatch<React.SetStateAction<number>>;
    handlePageChange: (isNext: boolean) => void;
    count: number;
}

const DataTableBottom: React.FC<DataTableBottomProps> = ({ page, setPage, pageSize, setPageSize, handlePageChange, count }) => {
    return (
        <TableBottomContainer>
            <DisplayPageSize>
                Displaying {page * pageSize - pageSize + 1} - {Math.min(page * pageSize, count)} of {count} results
            </DisplayPageSize>
            <PageSizeSwitchContainer>
                <PageSizeText>
                    Lots per page:
                </PageSizeText>
                <PageSizeSwitcher
                    value={pageSize}
                    onChange={(e) => {
                        setPageSize(Number(e.target.value));
                    }}
                    >
                    {[10, 20, 50, 100].map((size) => (
                    <option key={size} value={size}>
                            {size}
                        </option>
                    ))}
                </PageSizeSwitcher>
            </PageSizeSwitchContainer>
            <PageSwitchContainer>
                <SquareButton onClick={() => setPage(1)}><ChevronDoubleLeft /></SquareButton>
                <SquareButton onClick={() => handlePageChange(false)}><ChevronLeft /></SquareButton>
                <DisplayPage>
                    Page {page} of {Math.ceil(count / pageSize)}
                </DisplayPage>
                <SquareButton onClick={() => handlePageChange(true)}><ChevronRight /></SquareButton>
                <SquareButton onClick={() => setPage(Math.ceil(count / pageSize))}><ChevronDoubleRight /></SquareButton>
            </PageSwitchContainer>
        </TableBottomContainer>
    );
};

export default DataTableBottom;