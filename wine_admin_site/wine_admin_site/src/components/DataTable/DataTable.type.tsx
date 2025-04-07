export interface Column {
    header: string;
    accessor: string;
};

export interface TableProps<T> {
    columns: Column[];
    data: T[];
};