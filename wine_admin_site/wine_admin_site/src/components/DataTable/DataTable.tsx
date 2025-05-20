'use client';
import React from 'react';
import styled from 'styled-components';
import { TableProps } from './DataTable.type';

const TableComponentComtainer = styled.div`
    display: flex;
    flex-direction: column;
    width: 100%;
    margin-top: 30px;
`;

const TableContainer = styled.div`
    border-collapse: collapse;
`;

const Table = styled.table`
    width: 100%;
    border-radius: 10px;
    border: 1px solid #DED9D3;
`;

const TableHeaderRow = styled.tr`
    padding: 12px;
    background-color: #FEFAF9;
    color: white;
    text-align: left;
    font-weight: bold;
    border-radius: 10px 10px 0px 0px;
`;

const TableHeaderCell = styled.th`
    padding: 12px;
    background-color: #F5F1ED;
    color: #705C61;
    text-align: left;
    font-weight: 600;
    font-size: 15px;

    &:first-child {
        border-top-left-radius: 10px;
    }
        
    &:last-child {
        border-top-right-radius: 10px;
    }
`;

const TableRow = styled.tr`
    &:nth-child(even) {
        background-color: #F5F1ED;
    }
`;

const TableCell = styled.td`
    padding: 12px;
    text-align: left;
    max-width: 200px;
    word-break: break-word;
    white-space: normal;
    font-size: 14px;
`;

const DataTable = <T extends Record<string, any>>({ columns, data }: TableProps<T>) => {
    return (
        <TableComponentComtainer>
            <TableContainer>
                <Table>
                    <thead>
                        <TableHeaderRow>
                            {columns.map((col, idx) => (
                                <TableHeaderCell key={idx}>
                                    {col.header}
                                </TableHeaderCell>
                            ))}
                        </TableHeaderRow>
                    </thead>
                    <tbody>
                        {data.map((row, rowIndex) => (
                            <TableRow key={rowIndex}>
                                {columns.map((col, idx) => (
                                    <TableCell key={idx}>
                                        {row[col.accessor as keyof T]?.toString() ?? '-'}
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))}
                    </tbody>
                </Table>
            </TableContainer>
        </TableComponentComtainer>
    );
};

export default DataTable;
