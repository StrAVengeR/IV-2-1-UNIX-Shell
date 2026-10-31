#!/bin/bash
# Automatic tests for osh. Each test feeds stdin and checks stdout/stderr.
cd "$(dirname "$0")/.." || exit 1
OSH=./osh; pass=0; fail=0; T=$(mktemp -d)
check() { # name, expected-substring, actual
  if [[ "$3" == *"$2"* ]]; then echo "PASS $1"; pass=$((pass+1));
  else echo "FAIL $1 (expected '$2', got '$3')"; fail=$((fail+1)); fi; }
check T01_echo      "hello"           "$(printf 'echo hello\n' | $OSH)"
check T02_args      "a b c"           "$(printf 'echo a b c\n' | $OSH)"
check T03_empty     "ok"              "$(printf '\n\n  \necho ok\n' | $OSH)"
check T04_history0  "No commands in history." "$(printf '!!\n' | $OSH)"
check T05_bang      "hi
hi"                                   "$(printf 'echo hi\n!!\n' | $OSH)"
check T06_history   "2 echo b"        "$(printf 'echo a\necho b\nhistory\n' | $OSH)"
check T07_redirout  "data"            "$(printf "echo data > $T/o.txt\ncat $T/o.txt\n" | $OSH)"
check T08_redirin   "xyz"             "$(printf "echo xyz > $T/i.txt\ncat < $T/i.txt\n" | $OSH)"
check T09_nospace   "sp"              "$(printf "echo sp>$T/n.txt\ncat<$T/n.txt\n" | $OSH)"
check T10_pipe      "3"               "$(printf 'printf "a\\nb\\nc\\n" | wc -l\n' | $OSH)"
check T11_pipe3     "B"               "$(printf 'echo b | tr b B | cat\n' | $OSH)"
check T12_bg        "[bg] pid"        "$(printf 'sleep 0.2 &\n' | $OSH)"
check T13_bgdone    "[done]"          "$(printf 'sleep 0.1 &\nsleep 0.5\necho x\n' | $OSH)"
check T14_nocmd     "nosuchcmd_zz: No such file" "$(printf 'nosuchcmd_zz\n' | $OSH 2>&1)"
check T15_nofile    "nofile_zz: No such file"    "$(printf 'cat < nofile_zz\n' | $OSH 2>&1)"
check T16_synpipe   "syntax error"    "$(printf '| ls\n' | $OSH 2>&1)"
check T17_synredir  "missing file name" "$(printf 'ls >\n' | $OSH 2>&1)"
check T18_cd        "$T"              "$(printf "cd $T\npwd\n" | $OSH)"
check T19_exit      "before"          "$(printf 'echo before\nexit\necho after\n' | $OSH)"
check T20_longline  "line too long"   "$(python3 -c "print('a'*3000)" | $OSH 2>&1)"
# log test
OSH_LOG=$T/log.jsonl $OSH <<< $'echo x | cat' >/dev/null
check T21_log_spawn '"ev":"spawn"'    "$(cat $T/log.jsonl)"
check T22_log_exit  '"ev":"exit"'     "$(cat $T/log.jsonl)"
rm -rf "$T"
echo "RESULT: $pass passed, $fail failed"; [ $fail -eq 0 ]
