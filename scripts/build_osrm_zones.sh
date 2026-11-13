#!/usr/bin/env bash
# Préprocesse les données OSRM Madagascar pour chaque zone routière (zone1/2/3).
# Chaque zone a son propre profil Lua et son propre jeu de fichiers .osrm dans osrm-data/zoneN/.
# Nécessite Docker (image osrm/osrm-backend:latest).

set -euo pipefail

cd "$(dirname "$0")/.."
OSRM_DIR="$(pwd)/osrm-data"
PBF_FILE="madagascar-latest.osm.pbf"
IMAGE="osrm/osrm-backend:latest"

if [ ! -f "${OSRM_DIR}/${PBF_FILE}" ]; then
  echo "Erreur : ${OSRM_DIR}/${PBF_FILE} introuvable." >&2
  exit 1
fi

run_osrm() {
  docker run --rm -t -v "${OSRM_DIR}:/data" "${IMAGE}" "$@"
}

for zone in zone1 zone2 zone3; do
  echo "=========================================="
  echo " Préparation ${zone}"
  echo "=========================================="

  rm -rf "${OSRM_DIR}/${zone}"
  mkdir -p "${OSRM_DIR}/${zone}"
  cp "${OSRM_DIR}/${PBF_FILE}" "${OSRM_DIR}/${zone}/${PBF_FILE}"

  echo "[${zone}] osrm-extract"
  run_osrm osrm-extract -p "/data/profiles/car-${zone}.lua" "/data/${zone}/${PBF_FILE}"

  echo "[${zone}] osrm-partition"
  run_osrm osrm-partition "/data/${zone}/madagascar-latest.osrm"

  echo "[${zone}] osrm-customize"
  run_osrm osrm-customize "/data/${zone}/madagascar-latest.osrm"

  rm -f "${OSRM_DIR}/${zone}/${PBF_FILE}"
  echo "[${zone}] OK"
done

echo ""
echo "Terminé. Relance les conteneurs avec : docker compose up -d osrm-zone1 osrm-zone2 osrm-zone3"
