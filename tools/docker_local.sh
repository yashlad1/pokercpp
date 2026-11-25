#!/bin/bash
# Local-only check image for Apple Silicon: builds pokercpp:local-arm64 (native, fast)
# and runs the two bot tests inside it. The release image stays linux/amd64.
#   tools/docker_local.sh
cd "$(dirname "$0")/.."
REPO=$PWD
docker build --platform linux/arm64 -f chipzen/Dockerfile -t pokercpp:local-arm64 . || exit $?
rc=0
for t in test_bot_sdk.py test_v4.py; do
  docker run --rm --platform linux/arm64 -v "$REPO/chipzen/$t:/bot/$t" \
    --entrypoint sh pokercpp:local-arm64 -c "cd /bot && python $t"
  code=$?; echo "$t exit code: $code"; [ $code -ne 0 ] && rc=$code
done
exit $rc
