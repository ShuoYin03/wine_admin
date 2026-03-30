export const FxRatesFilterOptions: string[] = [
    "Rates From",
    "Rates To",
    "Date",
];

export const FxRatesOrderByOptions: Record<string, string> = {
    "": "",
    "Rates From (A→Z)": "rates_from",
    "Date (Newest First)": "-date",
    "Date (Oldest First)": "date",
};
