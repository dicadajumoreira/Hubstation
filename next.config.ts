import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: false,
    serverActions: {
      // Default é 1MB — fotos de síndico/gestor podem chegar a 5MB.
      bodySizeLimit: "8mb",
    },
  },
  // Empacota os SVGs da biblioteca Consvicta na serverless function
  // que faz fs.readFile no upload. Em Netlify/Vercel, public/ é
  // servido como estático no CDN mas NAO fica acessivel via Node fs
  // em runtime — esse trace inclui os arquivos no bundle da rota.
  outputFileTracingIncludes: {
    "/sindicompany/consvicta-assets": [
      "./public/consvicta-library/**/*",
    ],
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.supabase.co",
      },
    ],
  },
};

export default nextConfig;
