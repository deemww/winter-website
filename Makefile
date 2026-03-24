# general
mkfile_path := $(abspath $(firstword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))
current_abs_path := $(subst Makefile,,$(mkfile_path))

# pipeline constants
project_name := 2026-winter-bfi
port := 8501

# (Optional) load environment variables if you still need them for other tasks
-include .env

.PHONY: build run build-run clean deep-clean

# Build Docker image using pure Docker
build:
	docker build -t $(project_name) .

# Run the container
run:
	docker run -p $(port):$(port) $(project_name)

# Do both in one command
build-run: build run

# Stop and remove the specific container
clean:
	docker ps -a -q --filter ancestor=$(project_name) | xargs -r docker rm -f

# Completely remove the image to free up space
deep-clean: clean
	docker rmi -f $(project_name)