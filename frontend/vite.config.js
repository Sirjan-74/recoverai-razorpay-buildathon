import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  preview: {
    allowedHosts: [
      'trustworthy-joy-production-08d2.up.railway.app'
    ]
  }
})
