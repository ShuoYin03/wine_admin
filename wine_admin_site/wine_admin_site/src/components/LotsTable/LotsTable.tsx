'use client';
import React from 'react';
import styled from 'styled-components';
import { LotDisplayType } from '@/types/lotApi';

type TableProps = {
    columns: string[];
    data: LotDisplayType[];
};

const LwinTableContainer = styled.div`
    display: flex;
    flex-direction: column;
    padding: 20px;
    width: 100%;
    margin: 0 auto;
    background-color: #f9f9f9;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
`;

const Table = styled.table`
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
`;

const TableHeader = styled.th`
    padding: 12px;
    background-color:rgb(174, 24, 24);
    color: white;
    text-align: left;
    font-weight: bold;

`;

const TableRow = styled.tr`
    &:nth-child(even) {
        background-color: #f2f2f2;
    }
`;

const TableCell = styled.td`
    padding: 12px;
    border: 1px solid #ddd;
    text-align: left;
`;

const LwinTable: React.FC<TableProps> = ({ columns, data }) => {
    return (
        <LwinTableContainer>
            <h2>Lots Table</h2>
            <Table>
                <thead>
                    <tr>
                        {columns.map((column) => (
                            <TableHeader key={column}>{column}</TableHeader>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.map((row, rowIndex) => (
                        <TableRow key={rowIndex}>
                            {columns.map((column) => (
                                <TableCell key={column}>
                                    {row[column as keyof LotDisplayType]?.toString() ?? '-'}
                                </TableCell>
                            ))}
                        </TableRow>
                    ))}
                </tbody>
            </Table>
        </LwinTableContainer>
    );
};

export default LwinTable;
