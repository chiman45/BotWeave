import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  
  // Only use standalone output for Docker builds
  // Vercel deployments should NOT use this
  ...(process.env.DOCKER_BUILD === 'true' && { output: 'standalone' }),
  
  // Ensure proper image optimization
  images: {
    unoptimized: false,
  },
};

export default nextConfig;
