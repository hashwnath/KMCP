/** @type {import('next').NextConfig} */
// API URL injected at runtime via env var on the Next.js server.
// Defaults to the admin container's internal name when running in compose,
// fall back to localhost for `npm run dev`.
const apiTarget = process.env.ADMIN_API_URL || 'http://localhost:8081';

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      { source: '/api/:path*', destination: `${apiTarget}/api/:path*` },
    ];
  },
};
module.exports = nextConfig;
