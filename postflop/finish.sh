#!/bin/bash
# post-processing chain: site data -> validation -> report -> checks -> screenshots
# 需要先 `python3 -m http.server 18931 --directory site` (在 postflop/ 下) 給 check_ui / test_pages 用
set -e
cd "$(dirname "$0")/py"
echo "== build_site $(date)"; python3 build_site.py
echo "== validate"; python3 validate.py
echo "== consistency"; python3 consistency.py
echo "== make_report"; python3 make_report.py
echo "== assemble"; python3 assemble_report.py
echo "== check_data"; python3 ../check/check_data.py
echo "== check_ui"; node ../check/check_ui.js
echo "== screenshots"; mkdir -p ../screens
node ../check/test_pages.js
echo "== done $(date)"
