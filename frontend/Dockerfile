# ── Stage 1: Dev / Build ──
FROM node:20-alpine AS build

RUN npm config set registry https://registry.npmmirror.com

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ── Stage 2: Production (nginx) ──
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
