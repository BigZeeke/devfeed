# Frontend image for DevFeed: builds the React app with Node, then serves the
# built files with NGINX, which also proxies /api/ to the Django backend.
# Build context is frontend/ (the folder with package.json).
# Two stages: only the built dist/ folder reaches the final image, so Node,
# node_modules and the source code are left behind in the build stage.

# Stage 1: build the app on the current Node LTS line (26), slim Debian base
FROM node:26-slim AS build

WORKDIR /app

# Install dependencies first, in their own layer, so code-only changes reuse
# the cached install. npm ci installs exactly what package-lock.json lists.
COPY package.json package-lock.json ./
RUN npm ci

# Copy the source code (.dockerignore keeps node_modules, dist and .env out)
COPY . .

# Empty API URL: the app calls /api/ on the same origin it was loaded from,
# where NGINX proxies the request to Django. api.js already falls back to ""
# in a production build; setting it here makes that choice visible.
ENV VITE_API_URL=""
RUN npm run build

# Stage 2: serve the built files with NGINX (stable 1.30 line, Alpine base)
FROM nginx:1.30-alpine

# Replace the image's default site with the DevFeed config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy only the built app from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# NGINX listens on port 80 inside the container; the image's default command
# already starts it in the foreground
EXPOSE 80
