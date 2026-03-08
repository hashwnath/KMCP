const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081';

async function apiCall<T>(endpoint: string, options: RequestInit = {}): Promise<{ data?: T; error?: string }> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...options.headers as any };
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  if (token) headers['Authorization'] = `Bearer ${token}`;
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    const json = await res.json();
    return res.ok ? { data: json } : { error: json.error || 'Request failed' };
  } catch (err) { return { error: err instanceof Error ? err.message : 'Unknown error' }; }
}

export const login = (email: string, password: string) => apiCall('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
export const requestMagicLink = (email: string) => apiCall('/api/auth/magic-link/request', { method: 'POST', body: JSON.stringify({ email }) });
export const verifyMagicLink = (token: string) => apiCall('/api/auth/magic-link/verify', { method: 'POST', body: JSON.stringify({ token }) });
export const signup = (name: string, email: string, password: string) => apiCall('/api/auth/signup', { method: 'POST', body: JSON.stringify({ name, email, password }) });
export const getMe = () => apiCall('/api/tenants/me');
export const getSources = () => apiCall('/api/sources');
export const addSource = (data: any) => apiCall('/api/sources', { method: 'POST', body: JSON.stringify(data) });
export const deleteSource = (id: string) => apiCall(`/api/sources/${id}`, { method: 'DELETE' });
export const reindexSource = (id: string) => apiCall(`/api/sources/${id}/reindex`, { method: 'POST' });
export const updateSourceSchedule = (id: string, sync_schedule: string) => apiCall(`/api/sources/${id}/schedule`, { method: 'PUT', body: JSON.stringify({ sync_schedule }) });
export const getOverview = () => apiCall('/api/analytics/overview');
export const getGaps = () => apiCall('/api/analytics/gaps');
export const getTopQueries = () => apiCall('/api/analytics/top-queries');
export const getToolUsage = () => apiCall('/api/analytics/tool-usage');
export const getSettings = () => apiCall('/api/settings');
export const updateSettings = (data: any) => apiCall('/api/settings', { method: 'PUT', body: JSON.stringify(data) });
export const regenerateApiKey = () => apiCall('/api/settings/regenerate-key', { method: 'POST' });

// File upload: get presigned S3 URL, then PUT the file directly to S3
export async function uploadFile(file: File): Promise<{ key?: string; bucket?: string; error?: string }> {
  // Step 1: Get presigned URL from backend
  const { data, error } = await apiCall<{ upload_url: string; key: string; bucket: string }>(
    '/api/upload/presign',
    {
      method: 'POST',
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
        file_size_bytes: file.size,
        batch_count: 1,
      }),
    }
  );
  if (error || !data) return { error: error || 'Failed to get upload URL' };

  // Step 2: PUT file directly to S3 via presigned URL
  try {
    const resp = await fetch(data.upload_url, {
      method: 'PUT',
      body: file,
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
    });
    if (!resp.ok) return { error: `Upload failed: ${resp.status}` };
    return { key: data.key, bucket: data.bucket };
  } catch (err) {
    return { error: err instanceof Error ? err.message : 'Upload failed' };
  }
}
