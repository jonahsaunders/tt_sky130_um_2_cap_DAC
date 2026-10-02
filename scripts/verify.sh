#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PDK=sky130A PDK_ROOT=/foss/pdks PDKPATH=/foss/pdks/sky130A OMP_NUM_THREADS=1
: "${TT_SUPPORT_TOOLS:?Set TT_SUPPORT_TOOLS to a clone of TinyTapeout/tt-support-tools}"
export OMP_THREAD_LIMIT=1 OPENBLAS_NUM_THREADS=1
python3 "$ROOT/scripts/physical_verify.py"
python3 "$ROOT/scripts/rebuild_verify.py"
python3 "$ROOT/scripts/extract.py"
python3 "$ROOT/scripts/check_layout.py"
python3 "$ROOT/scripts/check_schematic.py"
python3 "$ROOT/scripts/prepare_models.py"
cd "$TT_SUPPORT_TOOLS/precheck"
python3 precheck.py --gds "$ROOT/gds/tt_um_jonah_suarez_dac.gds" --tech sky130A > "$ROOT/verification/precheck_console.log" 2>&1
cp -r reports/. "$ROOT/verification/precheck/"
cd "$TT_SUPPORT_TOOLS"
python3 - "$ROOT" <<'PY'
import sys
from project_checks import check_project_docs
check_project_docs(sys.argv[1], 'sky130A')
PY
for suite in ac pvt mc full; do
    python3 "$ROOT/scripts/qualify_suite.py" "$suite" --jobs 4
done
python3 "$ROOT/scripts/special.py"
python3 "$ROOT/scripts/buffer_noise.py"
python3 "$ROOT/scripts/release_report.py"
