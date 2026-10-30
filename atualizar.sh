#!/bin/sh
set -eu

script_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "$#" -eq 0 ]; then
    exec "$script_directory/erpctl" deploy production
fi
exec "$script_directory/erpctl" update production "$@"
