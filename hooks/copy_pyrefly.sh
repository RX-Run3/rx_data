#!/usr/bin/env bash

set -e

for project in src/*/; do
    cp pyrefly.toml "$project/pyrefly.toml";
    git add $project/pyrefly.toml
done
