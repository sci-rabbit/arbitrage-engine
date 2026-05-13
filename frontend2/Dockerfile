FROM node:20-alpine AS builder

WORKDIR /app
COPY frontend2/package.json ./
RUN npm install --ignore-scripts
COPY frontend2/index.html ./
COPY frontend2/vite.config.ts ./
COPY frontend2/tsconfig.json ./
COPY frontend2/tailwind.config.js ./
COPY frontend2/postcss.config.js ./
COPY frontend2/src ./src
RUN npm run build

FROM nginx:stable-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend2/nginx.conf.template /etc/nginx/templates/default.conf.template

RUN chmod -R 755 /usr/share/nginx/html
# nginx official image processes /etc/nginx/templates/*.template via envsubst on startup
# Set USER_API_URL and AGGREGATION_API_URL as container env vars in docker-compose

EXPOSE 80 443