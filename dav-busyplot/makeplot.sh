#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

cd "$(dirname "$0")"

docker build .

mkdir -p output
docker run --rm -ti -u "$UID" \
    -v "$PWD:/src:ro" \
    -v "$PWD/output:/output" \
    --workdir /src \
    "$(docker build -q .)" \
    python3 dav-busyplot.py dav-busylog.sqlite /output/dav-busyplot.html
