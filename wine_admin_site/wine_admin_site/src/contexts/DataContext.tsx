// 'use client';
// import React, { createContext, useContext, useState } from 'react';

// interface DataContextType {
//     data: object[];
//     setData: React.Dispatch<React.SetStateAction<object[]>>;
// }

// const DataContext = createContext<DataContextType | undefined>(undefined);

// export const DataProvider = ({ children }: { children: React.ReactNode }) => {
//     const [data, setData] = useState<object[]>([]);

//     return (
//         <DataContext.Provider
//             value={{
//                 data,
//                 setData,
//             }}
//         >
//             {children}
//         </DataContext.Provider>
//     );
// };

// export const useDataContext = (): DataContextType => {
//     const context = useContext(DataContext);
//     if (!context) {
//         throw new Error('useFilterContext must be used within a FilterProvider');
//     }
//     return context;
// };

// utils/createDataContext.ts
import React, { createContext, useContext, useState, useMemo } from 'react';

export function createDataContext<T>(
    extractPrice?: (item: T) => number
) {
    const DataContext = createContext<{
        data: T[];
        setData: React.Dispatch<React.SetStateAction<T[]>>;
        maxPrice: number;
        minPrice: number;
    } | undefined>(undefined);

    const DataProvider = ({ children }: { children: React.ReactNode }) => {
        const [data, setData] = useState<T[]>([]);

        const { max, min } = useMemo(() => {
            if (!extractPrice || data.length === 0) return { max: 0, min: 0 };
      
            let max = -Infinity;
            let min = Infinity;
            for (const item of data) {
              const price = extractPrice(item);
              if (price > max) max = price;
              if (price < min) min = price;
            }
            return { max, min };
          }, [data]);

        return (
            <DataContext.Provider 
                value={{ 
                    data, 
                    setData,
                    maxPrice: max,
                    minPrice: min,
                }}>
                {children}
            </DataContext.Provider>
        );
    };

    const useDataContext = () => {
        const context = useContext(DataContext);
        if (!context) {
            throw new Error("useData must be used within a Provider");
        }
        return context;
    };

    return { DataProvider, useDataContext };
}
