const formatAmount = (value?: number) => {
    if (value === null || value === undefined || isNaN(value)) return '-';
    return value.toLocaleString();
}

export default formatAmount;