#!/usr/bin/env bash

if [ ! -d scripts ]; then
    echo "This script needs to be called from the root folder, i.e. ./scripts/build-docker.sh"
    exit 1
fi

BRANCH=$(git symbolic-ref --short HEAD)
COMMIT=$(git rev-parse HEAD)
COMMIT_COUNT=$(git rev-list HEAD --count)
IMAGE_NAME=pajbot1:latest

echo docker build --build-arg=COMMIT="$COMMIT" --build-arg=BRANCH="$BRANCH" --build-arg=COMMIT_COUNT="$COMMIT_COUNT" -t "$IMAGE_NAME" .
