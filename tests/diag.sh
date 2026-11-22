#!/bin/bash
# Оношилгоо: гацаж байгаа шалтгааныг олно. Ажиллуулах: bash tests/diag.sh
cd "$(dirname "$0")/.." || exit 1
echo "== орчин"; python3 --version; gcc --version | head -1; which ps || echo "ps БАЙХГҮЙ"
echo "== build"; make 2>&1 | tail -2
echo "== 1. shell (сервергүй)"
printf 'echo hi\n' | OSH_PROTO=1 timeout 5 ./osh 2>&1 | cat -v; echo "rc=${PIPESTATUS[1]} (124 = гацсан)"
echo "== 2. сервер"
pkill -f ui/server.py 2>/dev/null; pkill -x osh 2>/dev/null; sleep 0.5
python3 ui/server.py >/tmp/diag_srv.log 2>&1 &
SP=$!; sleep 2
for c in pwd 'echo hi | tr a-z A-Z | cat'; do
  echo "-- cmd: $c"
  curl -s -m 10 -H 'Host: 127.0.0.1:8765' -H 'Content-Type: application/json' \
       -d "{\"cmd\":\"$c\"}" http://127.0.0.1:8765/api/run; echo " (curl rc=$?, 28 = гацсан)"
done
echo "-- tree"; curl -s -m 10 -H 'Host: 127.0.0.1:8765' http://127.0.0.1:8765/api/tree | head -c 400; echo
echo "== серверийн log"; cat /tmp/diag_srv.log
echo "== процессууд"; ps -ef | grep -E "osh|server.py" | grep -v grep
kill $SP 2>/dev/null; pkill -x osh 2>/dev/null
