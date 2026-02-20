#!/bin/bash
set -eo pipefail

echo "============================================================"
echo " Building Medusa Base Image (my-registry/medusa-base:latest)"
echo "============================================================"

# Create temporary build directory
BUILD_DIR=$(mktemp -d)
echo "=> Created build directory at $BUILD_DIR"

# Clone Medusa Starter
echo "=> Cloning medusajs/medusa-starter-default..."
git clone --depth 1 https://github.com/medusajs/medusa-starter-default.git "$BUILD_DIR"

cd "$BUILD_DIR"

# Create start.sh script
echo "=> Creating start.sh..."
cat > start.sh << 'EOF'
#!/bin/sh
echo "=> Running migrations..."
npx medusa db:migrate

echo "=> Starting Medusa backend..."
yarn start
EOF
chmod +x start.sh

# Create modern Dockerfile for Medusa v2
echo "=> Creating Dockerfile..."
cat > Dockerfile << 'EOF'
FROM node:20-alpine

WORKDIR /app

# Install native dependencies required by some Node modules
RUN apk add --no-cache python3 make g++ 

COPY package.json yarn.lock ./
# Medusa starter uses yarn.lock
RUN yarn install --frozen-lockfile

COPY . .

# Build the application (compiles TypeScript to JS & builds admin UI)
RUN yarn build

EXPOSE 9000

# Set Node environment
ENV NODE_ENV=production

# Run start script
CMD ["./start.sh"]
EOF

# Create .dockerignore
echo "=> Creating .dockerignore..."
cat > .dockerignore << 'EOF'
node_modules
.git
.gitignore
README.md
dist
build
EOF

# Build image
echo "=> Building Docker image..."
docker build -t my-registry/medusa-base:latest .

# Cleanup
cd - > /dev/null
rm -rf "$BUILD_DIR"

echo "============================================================"
echo " Successfully built my-registry/medusa-base:latest!"
echo "============================================================"
