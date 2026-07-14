#!/usr/bin/env bash
set -Eeuo pipefail

readonly APP_DIR="/opt/chechen-power-notify"
readonly APP_USER="chechen-power"
readonly BRANCH="main"
readonly SERVICE="chechen-power-notify.service"
readonly LOCK_FILE="/run/lock/chechen-power-notify-deploy.lock"

exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    echo "Another deployment is already running." >&2
    exit 1
fi

run_as_app() {
    runuser -u "${APP_USER}" -- "$@"
}

cd "${APP_DIR}"

requested_revision="${1:-}"
if [[ ! "${requested_revision}" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Deployment aborted: a full Git commit SHA is required." >&2
    exit 1
fi

if [[ -n "$(run_as_app git status --porcelain --untracked-files=no)" ]]; then
    echo "Deployment aborted: the production checkout has tracked changes." >&2
    exit 1
fi

run_as_app git fetch --prune origin "${BRANCH}"

previous_revision="$(run_as_app git rev-parse HEAD)"
target_revision="$(run_as_app git rev-parse "${requested_revision}^{commit}")"
branch_revision="$(run_as_app git rev-parse "origin/${BRANCH}")"

if [[ "${previous_revision}" == "${target_revision}" ]]; then
    echo "Production is already at ${target_revision}."
    systemctl is-active --quiet "${SERVICE}"
    exit 0
fi

if ! run_as_app git merge-base --is-ancestor "${target_revision}" "${branch_revision}"; then
    echo "Deployment aborted: ${target_revision} is not on origin/${BRANCH}." >&2
    exit 1
fi

if ! run_as_app git merge-base --is-ancestor "${previous_revision}" "${target_revision}"; then
    echo "Deployment aborted: ${target_revision} is not a fast-forward update." >&2
    exit 1
fi

dependencies_changed=0
if run_as_app git diff --name-only "${previous_revision}..${target_revision}" | grep -qx "pyproject.toml"; then
    dependencies_changed=1
fi

run_as_app git merge --ff-only "${target_revision}"

if [[ "${dependencies_changed}" -eq 1 ]]; then
    run_as_app .venv/bin/pip install --disable-pip-version-check -e .
fi

run_as_app .venv/bin/python -m compileall -q app
run_as_app .venv/bin/alembic upgrade head

systemctl restart "${SERVICE}"
sleep 10
systemctl is-active --quiet "${SERVICE}"

echo "Deployed ${target_revision}; ${SERVICE} is active."
