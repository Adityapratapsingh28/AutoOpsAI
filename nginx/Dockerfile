# Stage 1: Build the React frontend
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend-react/package*.json ./
RUN npm install
COPY frontend-react/ .
RUN npm run build

# Stage 2: Serve securely with Nginx
FROM nginx:alpine

# Install openssl to generate self-signed certificates
RUN apk add --no-cache openssl

# Create SSL directory
RUN mkdir -p /etc/nginx/ssl

# Generate a self-signed certificate valid for 365 days
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/nginx.key \
    -out /etc/nginx/ssl/nginx.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=localhost"

# Copy the custom NGINX configuration
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built React app from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80 443
