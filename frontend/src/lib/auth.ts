export const setToken = (t: string) => typeof window !== 'undefined' && localStorage.setItem('token', t);
export const getToken = () => typeof window !== 'undefined' ? localStorage.getItem('token') : null;
export const clearToken = () => typeof window !== 'undefined' && localStorage.removeItem('token');
export const isAuthenticated = () => !!getToken();
