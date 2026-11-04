#!/usr/bin/env bash

check()
{
    local project_dir=$1
    if [[ ! -d $project_dir ]];then
        echo "Project path $project_dir not found"
        exit 1
    fi

    (
        cd "$project_dir" || exit 1
        pyrefly check
    )
}

check src/fitter
