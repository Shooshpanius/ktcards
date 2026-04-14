let csrfToken: string | null = null;

async function fetchCsrfToken(): Promise<string> {
    const r = await fetch('/api/auth/csrf');
    if (!r.ok) throw new Error('Failed to fetch CSRF token');
    const data = await r.json() as { token: string };
    return data.token;
}

export async function getCsrfToken(): Promise<string> {
    if (!csrfToken) {
        csrfToken = await fetchCsrfToken();
    }
    return csrfToken;
}

const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

export async function csrfFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const method = (init?.method ?? 'GET').toUpperCase();
    if (MUTATING_METHODS.has(method)) {
        const token = await getCsrfToken();
        init = {
            ...init,
            headers: {
                ...init?.headers,
                'X-CSRF-TOKEN': token,
            },
        };
    }
    return fetch(input, init);
}
