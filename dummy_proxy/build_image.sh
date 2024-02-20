# Build multiarch image (https://www.docker.com/blog/multi-arch-images/)

docker buildx create --name mybuilder
docker buildx use mybuilder
docker buildx inspect --bootstrap

docker buildx build --platform linux/arm64,linux/amd64 -t hectorcadavid/dummy-v6-server-proxy --push .
