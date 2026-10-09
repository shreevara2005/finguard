# ---- Build stage ----
FROM node:22-slim AS builder
WORKDIR /build
COPY package.json ./
RUN npm install
COPY . .
# VITE_API_BASE_URL is baked in at build time (Vite env vars are compile-time)
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# ---- Runtime stage ----
FROM nginx:alpine
COPY --from=builder /build/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
