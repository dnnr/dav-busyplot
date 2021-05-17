#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

if [[ $# != 1 ]]; then
    echo "Usage: $(basename "$0") <database>"
    exit 1
fi

dbfile="$(realpath "$1")"

cd "$(dirname "$0")"

docker build .

mkdir -p output
docker run --rm -ti -u "$UID" \
    -v "$PWD:/src:ro" \
    -v "$PWD/output:/output" \
    -v "$(dirname "$dbfile")":/db:ro \
    --workdir /src \
    "$(docker build -q .)" \
    python3 dav-busyplot.py --filename=index.html "/db/$(basename "$dbfile")" /output
