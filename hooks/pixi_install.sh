#!/usr/bin/env bash

if ! command -v pixi > /dev/null 2>&1;then
    echo "Pixi not found, cannot run installation"
    exit 1
fi

pixi install
