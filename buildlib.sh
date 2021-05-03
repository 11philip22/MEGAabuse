#!/usr/bin/env bash

docker build -f Arch.Dockerfile .
id=$(docker images | awk '{print $3}' | awk 'NR==2')
docker run --rm --entrypoint cat "${id}" /sdk/bindings/python/build/lib/mega/_mega.so > megaabuse/mega/_mega.so
docker run --rm --entrypoint cat "${id}" /sdk/bindings/python/build/lib/mega/libmega.so > megaabuse/mega/libmega.so