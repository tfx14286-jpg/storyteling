/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/python/:path*",
        destination: "/api/:path*",
      },
    ]
  },
}
module.exports = nextConfig
