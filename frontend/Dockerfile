FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .

ARG VITE_API_URL=""
ARG VITE_GOOGLE_CLIENT_ID=""
ENV VITE_API_URL=$VITE_API_URL VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
RUN npm run build

FROM nginx:1.27-alpine
ENV API_UPSTREAM=http://api:8000
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
