import { fileURLToPath, URL } from 'node:url';

import { defineConfig } from 'vite';
import plugin from '@vitejs/plugin-react';
import { env } from 'process';

// Force proxy target to use HTTP only. Ignore any HTTPS port env vars.
const target = env.ASPNETCORE_URLS ? env.ASPNETCORE_URLS.split(';')[0].replace(/^https:/, 'http:') : 'http://localhost:5069';

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [plugin()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    server: {
        proxy: {
            '^/api': {
                target,
                changeOrigin: true,
                secure: false
            },
            '^/uploads': {
                target,
                changeOrigin: true,
                secure: false
            }
        },
        port: parseInt(env.DEV_SERVER_PORT || '56485'),
        // HTTPS disabled — serve over HTTP only
    //    https: false
    }
})
