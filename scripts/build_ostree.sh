#!/usr/bin/env bash
# Build extra-data Flatpak shells into a GPG-signed OSTree archive-z2 repository.
set -euo pipefail

REPO_DIR="${1:?usage: $0 <ostree-repo-dir>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -z "${FLATPAK_GPG_PRIVATE_KEY:-}" ]; then
  echo "ERROR: FLATPAK_GPG_PRIVATE_KEY environment variable is required" >&2
  exit 1
fi

WORK_TMP="$(mktemp -d)"
GNUPGHOME="${WORK_TMP}/gnupg"
mkdir -p "${GNUPGHOME}" "${REPO_DIR}"
chmod 700 "${GNUPGHOME}"
trap 'rm -rf "${WORK_TMP}"' EXIT
export GNUPGHOME

printf '%s\n' "${FLATPAK_GPG_PRIVATE_KEY}" | gpg --batch --import >/dev/null 2>&1
FPR="$(gpg --batch --list-secret-keys --with-colons | awk -F: '/^fpr:/{print $10; exit}')"
if [ -z "${FPR}" ]; then
  echo "ERROR: Failed to extract GPG fingerprint from imported secret key" >&2
  exit 1
fi
echo "[ostree] Signing with GPG fingerprint: ${FPR}"

if [ ! -f "${REPO_DIR}/config" ]; then
  ostree --repo="${REPO_DIR}" init --mode=archive-z2
fi

flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

for app_json in "${ROOT}"/registry/*/app.json; do
  app_dir="$(dirname "${app_json}")"
  app_id="$(basename "${app_dir}")"
  manifest="${app_dir}/${app_id}.yml"
  echo "::group::Building extra-data wrapper for ${app_id}"
  (
    cd "${app_dir}"
    flatpak-builder \
      --force-clean \
      --disable-rofiles-fuse \
      --user \
      --install-deps-from=flathub \
      --repo="${REPO_DIR}" \
      --default-branch=stable \
      --state-dir="${WORK_TMP}/state" \
      --gpg-sign="${FPR}" \
      --gpg-homedir="${GNUPGHOME}" \
      "${WORK_TMP}/build-${app_id}" \
      "${manifest}"
  )
  echo "::endgroup::"
done

flatpak build-update-repo \
  --title="Flatpak Hub (helloshu)" \
  --generate-static-deltas \
  --prune \
  --gpg-sign="${FPR}" \
  --gpg-homedir="${GNUPGHOME}" \
  "${REPO_DIR}"

if [ ! -s "${REPO_DIR}/summary" ] || [ ! -s "${REPO_DIR}/summary.sig" ]; then
  echo "ERROR: OSTree summary or summary.sig missing in ${REPO_DIR}" >&2
  exit 1
fi
echo "[ostree] Signed OSTree repository ready at ${REPO_DIR}"
