#!/bin/sh
set -eu

# Download only the pinned, checksum-verified local Spike runtime. No global install.
spike_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
binary_dir="$spike_root/.runtime-bin"
mkdir -p "$binary_dir"
case "$(uname -sm)" in
  "Darwin arm64")
    asset=agentgateway-darwin-arm64
    expected=da432d35bd696da0564f7b2b6bbc783542b6b9c616d6c0c4d4c3daef9dfa11a1
    ;;
  "Linux aarch64")
    asset=agentgateway-linux-arm64
    expected=61f12dbb99669aa4b97b85a0040183fe4b098fa0a82a8c389665fe606517c13e
    ;;
  *)
    echo "Unsupported Spike platform; do not substitute an unpinned binary." >&2
    exit 1
    ;;
esac
binary="$binary_dir/agentgateway-v1.5.0"
if [ ! -f "$binary" ]; then
  curl --fail --location --retry 2 --connect-timeout 15 --max-time 180 \
    "https://github.com/agentgateway/agentgateway/releases/download/v1.5.0/$asset" \
    --output "$binary.download"
  actual=$(shasum -a 256 "$binary.download" | awk '{print $1}')
  [ "$actual" = "$expected" ] || { echo "SHA256 mismatch; binary not activated." >&2; exit 1; }
  mv "$binary.download" "$binary"
fi
actual=$(shasum -a 256 "$binary" | awk '{print $1}')
[ "$actual" = "$expected" ] || { echo "Cached binary SHA256 mismatch." >&2; exit 1; }
chmod u+x "$binary"
"$binary" --version
echo "Verified SHA256: $actual"
