import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: attach JWT from localStorage
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("ovulite_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: on 401, clear token and redirect to /login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("ovulite_token");
      // Let the app-level auth provider handle navigation consistently.
      window.dispatchEvent(new CustomEvent("ovulite:unauthorized"));
    }
    return Promise.reject(error);
  }
);

export default api;

/**
 * Fetch every page of a paginated list endpoint.
 *
 * The CRUD routers cap `page_size` at 100, so a reference list longer than
 * that (recipients is ~400) silently truncates if you request one page and
 * assume it is everything. A truncated dropdown is worse than a slow one: the
 * missing rows look like they do not exist.
 */
export async function fetchAllPages<T>(
  url: string,
  params: Record<string, unknown> = {},
  pageSize = 100,
  maxPages = 50
): Promise<T[]> {
  const out: T[] = [];
  for (let page = 1; page <= maxPages; page += 1) {
    const { data } = await api.get<{ items?: T[]; pages?: number }>(url, {
      params: { ...params, page, page_size: pageSize },
    });
    const items = data.items ?? [];
    out.push(...items);
    if (items.length < pageSize || (data.pages !== undefined && page >= data.pages)) break;
  }
  return out;
}
