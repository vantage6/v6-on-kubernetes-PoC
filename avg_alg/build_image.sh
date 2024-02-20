# Build x86 image

#docker build . -t hectorcadavid/avg-alg-x86
#docker push  hectorcadavid/avg-alg-x86


# Build multiarch image (https://www.docker.com/blog/multi-arch-images/)

docker buildx create --name mybuilder
docker buildx use mybuilder
docker buildx inspect --bootstrap

docker buildx build --platform linux/arm64,linux/amd64,linux/amd64/v2,linux/arm/v7,linux/arm/v6 -t hectorcadavid/v6_average_algorithm --push .
