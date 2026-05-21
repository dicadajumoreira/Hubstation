import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: false,
    serverActions: {
      // Default é 1MB. Fotos de síndico/gestor chegam a ~5MB e zips de
      // fontes de marca podem passar disso — acima do teto o erro é de
      // página (reload), antes do nosso try/catch. Por isso 20MB.
      bodySizeLimit: "20mb",
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
    "/sindicompany/assets": [
      "./public/sindicompany-library/**/*",
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
