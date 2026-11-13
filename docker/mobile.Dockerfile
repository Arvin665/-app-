FROM node:22-alpine AS web-build
WORKDIR /app
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY mobile-app/package*.json ./
RUN npm ci
COPY mobile-app ./
RUN npm run build:h5

FROM nginx:1.27-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=web-build /app/dist/build/h5 /usr/share/nginx/html
EXPOSE 80
