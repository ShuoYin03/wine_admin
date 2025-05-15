export type ApiPayload = {
    filters: object;
    order_by: object;
    page: number;
    page_size: number;
}

export type ApiResponse = {
    status_code: number;
}

export type ApiErrorResponse = ApiResponse & {
    error_message: string;
}