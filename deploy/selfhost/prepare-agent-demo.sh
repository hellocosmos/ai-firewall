#!/bin/sh
# Synthetic fixture only. Never mount this wrapper for a real destination.
set -eu
umask 077
printf '%s' 'synthetic-target-token' > /state/synthetic-target.token
exec python -m asr_proxy.selfhost.main "$@"
