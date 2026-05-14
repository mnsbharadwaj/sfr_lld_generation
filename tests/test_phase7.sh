#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf out_patch
PYTHONPATH=src python -m ipxact_lld_gen.cli --excel sample/ipxact_sample.xlsx --sfr-header sample/sfr_new.h --existing-lld sample/old_lld.h --sfr-diff sample/sfr.diff --out out_patch

grep -q "static inline void dma_ctrl_start_set" out_patch/expected_lld.h
grep -q "static inline uint32_t dma_ctrl_start_get" out_patch/expected_lld.h
grep -q "static inline int dma_start" out_patch/expected_lld.h
grep -q "customer_private_debug_api" out_patch/patched_lld.h
grep -q "static inline void dma_ctrl_start_set" out_patch/patched_lld.h
echo "Phase 7.1 header-only static inline smoke test passed"
