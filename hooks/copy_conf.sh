#!/usr/bin/env bash

for project in src/*/; do
    cp pyrefly.toml "$project/pyrefly.toml";
    git add $project/pyrefly.toml
done
