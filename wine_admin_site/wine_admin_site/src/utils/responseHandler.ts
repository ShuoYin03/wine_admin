export const handleResponse = async (response: object) => {
    const result: string[] = [];
    if (Array.isArray(response)) {
        result.push(response.join(','));
        
    } else {
        for (const value of Object.values(response)) {
            result.push(String(value));
        }
    }
    return result;
};
