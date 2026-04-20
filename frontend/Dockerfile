# frontend/Dockerfile
# ─────────────────────
# Development container for the React app.
# Uses Node 18 LTS — the minimum version required by react-scripts 5.

FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files first for Docker layer caching.
# node_modules is only reinstalled when package.json changes.
COPY package.json package-lock.json* ./
RUN npm install

# Copy the rest of the source code.
# In docker-compose.yml we mount ./src as a volume for hot-reload,
# so this COPY mainly matters for standalone `docker build` usage.
COPY . .

# Expose the React dev server port
EXPOSE 3000

# Start the React development server.
# CHOKIDAR_USEPOLLING=true is required inside Docker on some systems
# (especially WSL2 / macOS) for hot-reload to detect file changes.
ENV CHOKIDAR_USEPOLLING=true
CMD ["npm", "start"]