#!/usr/bin/env bash

if ! command -v ruff > /dev/null 2>&1; then
    echo "Ruff not found"
    exit 1
fi

ruff check --fix .
