import type { NextConfig } from "next";

const API = process.env.AGENT_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // proxy para a API do agente — evita CORS e mantém tudo em mesma origem
  async rewrites() {
    return [
      { source: "/agent/:path*", destination: `${API}/:path*` },
    ];
  },
};

export default nextConfig;
