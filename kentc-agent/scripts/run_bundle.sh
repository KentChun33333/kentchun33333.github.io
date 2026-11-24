#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
    agent) module=kentc_agent.cli ;;
    studio) module=kentc_studio.server ;;
    breezeman) module=kentc_breezeman.server ;;
    -h|--help) printf 'Usage: bash run.sh {agent|studio|breezeman} [args...]\n'; exit 0 ;;
    *) printf 'Usage: bash run.sh {agent|studio|breezeman} [args...]\n' >&2; exit 2 ;;
esac
shift

if [[ $(uname -s) != Linux || $(uname -m) != aarch64 ]] || ! getconf GNU_LIBC_VERSION >/dev/null 2>&1; then
    printf 'This bundle requires glibc-based Linux ARM64 (aarch64).\n' >&2
    exit 1
fi
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
unset PYTHONHOME

# Runtime prefixes are fixed in place; the original ZIP can be extracted anywhere.
(
    flock -x 9
    if [[ -f "$root/env/.bundle-prefix" ]] && [[ $(<"$root/env/.bundle-prefix") == "$root/env" ]]; then
        exit 0
    fi
    if ! mkdir -- "$root/env"; then
        printf 'The runtime is incomplete or was moved. Extract a fresh copy of the ZIP.\n' >&2
        exit 1
    fi
    trap 'rm -rf -- "$root/env"' EXIT
    tar -xzf "$root/runtime.tar.gz" -C "$root/env"
    "$root/env/bin/python" -E -s "$root/env/bin/conda-unpack"
    printf '%s\n' "$root/env" > "$root/env/.bundle-prefix"
    trap - EXIT
) 9>"$root/.runtime-lock"

export PATH="$root/env/bin:$PATH"
export PYTHONPATH="$root/src" PYTHONNOUSERSITE=1
exec "$root/env/bin/python" -P -m "$module" "$@"
