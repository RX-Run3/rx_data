#!/usr/bin/env bash

for project in src/*/; do
    cp pyrefly.toml "$project/pyrefly.toml";
done

git add .
