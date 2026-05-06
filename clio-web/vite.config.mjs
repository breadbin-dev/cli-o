import { defineConfig } from 'vite'

export default defineConfig({
    build: {
        rollupOptions: {
            input: {
                main: 'index.html',
                login: 'login/login.html',
                not_found: 'not_found.html',
            }
        }
    }
})