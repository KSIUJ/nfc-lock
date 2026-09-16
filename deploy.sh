#!/usr/bin/env bash
set -euo pipefail

# Deploys this repo's source files to the lock's Raspberry Pi under
# /opt/nfc-lock, without touching anything that must survive an update:
# real config/secrets, the on-disk card/event cache, the venv, etc.
#
# Usage: ./deploy.sh [--dry-run] [--restart] [host]
#
#   --dry-run   show what would change without copying anything
#   --restart   restart the nfc-lock systemd service afterwards
#   host        ssh target (default: ksi-lock)

HOST="ksi-lock"
DEST="/opt/nfc-lock"
DRY_RUN=()
RESTART=0

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=(--dry-run) ;;
        --restart) RESTART=1 ;;
        -h|--help)
            sed -n '2,13p' "$0"
            exit 0
            ;;
        *) HOST="$arg" ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Anything below is excluded from the transfer entirely, so rsync --delete
# never touches it on the remote side either - only untracked/removed
# *source* files get cleaned up.
EXCLUDES=(
    --exclude '.git/'
    --exclude '.gitignore'
    --exclude '__pycache__/'
    --exclude '*.pyc'
    --exclude 'deploy.sh'
    # Real config/secrets (config-example/ ships in the repo, config/ is the
    # deployed copy - see README step 6).
    --exclude 'config/'
    # Legacy mTLS client cert dir; may still exist on already-deployed hosts.
    --exclude 'cert/'
    # On-disk card list / event queue used for offline decisions - must
    # persist across deploys (see auth.py).
    --exclude 'cache/'
    --exclude 'venv/'
    # Compiled on-device from reader.c via `make`; not part of the source tree.
    --exclude 'reader'
)

echo "Deploying $SCRIPT_DIR/ to $HOST:$DEST/"
echo "Preserved on remote: config/, cert/, cache/, venv/, compiled reader"

ssh "$HOST" "mkdir -p '$DEST'"

rsync -avzc --delete "${DRY_RUN[@]+"${DRY_RUN[@]}"}" "${EXCLUDES[@]}" \
    "$SCRIPT_DIR/" "$HOST:$DEST/"

if [[ ${#DRY_RUN[@]} -gt 0 ]]; then
    echo "Dry run only - nothing was copied."
    exit 0
fi

if [[ "$RESTART" -eq 1 ]]; then
    echo "Restarting nfc-lock service on $HOST"
    ssh "$HOST" 'systemctl restart nfc-lock'
fi
