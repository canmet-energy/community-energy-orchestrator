# Frontend Dockerfile for production build
FROM node:18-bookworm AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including devDependencies needed for build)
# Configure npm for environments with SSL issues (like dev containers)
# Use npm ci for reproducible builds
RUN npm config set strict-ssl false && npm ci

# Copy source code
COPY . .

# Build for production
RUN npm run build

# Production stage - serve with nginx
FROM nginx:alpine

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config (optional - for SPA routing)
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
