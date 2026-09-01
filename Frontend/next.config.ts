import type { NextConfig } from "next";

const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.clerk.accounts.dev https://*.clerk.com https://checkout.razorpay.com https://va.vercel-scripts.com",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "img-src 'self' data: blob: https://img.clerk.com https://*.clerk.com",
  "connect-src 'self' https://*.clerk.accounts.dev https://*.clerk.com https://checkout.razorpay.com https://api.razorpay.com https://lumberjack.razorpay.com",
  "frame-src 'self' https://*.clerk.accounts.dev https://*.clerk.com https://api.razorpay.com https://checkout.razorpay.com",
  "worker-src 'self' blob:",
  "frame-ancestors 'none'",
].join('; ')

const nextConfig: NextConfig = {
  /* config options here */

  // Only use standalone output for Docker builds
  // Vercel deployments should NOT use this
  ...(process.env.DOCKER_BUILD === 'true' && { output: 'standalone' }),

  // Ensure proper image optimization
  images: {
    unoptimized: false,
  },

  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Content-Security-Policy', value: csp },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
};

export default nextConfig;
