export const handleResponse = async (response: object) => {
    const result: string[] = [];
    if (Array.isArray(response)) {
        result.push(response.join(','));
        
    } else {
        for (const [_, value] of Object.entries(response)) {
            result.push(String(value));
        }
    }
    return result;
};
