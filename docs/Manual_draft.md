# F.CSM302 — БИЕ ДААЛТ 1 — MANUAL · IV-2-1 UNIX Shell

# А. Хэрэглэгчийн заавар
## A1. Програмын зорилго
`osh` бол UNIX shell. Browser UI нь shell-ийн ажиллуулсан процессуудыг PID-тай нь мод хэлбэрээр харуулна.
## A2. Дэмжих орчин
Linux (Ubuntu), macOS; Windows-д WSL. Хөтөч: Chrome/Firefox/Edge-ийн сүүлийн хувилбар.
## A3. Нээх алхам
1. `make` (osh бүтээнэ)
2. `python3 ui/server.py`
3. Хөтчөөр `http://127.0.0.1:8765` нээнэ.
## A4. Дэлгэцийн бүтэц
Зүүн: терминал, команд оруулах талбар, жишээ товчууд, Reset. Баруун: процессын мод, history, төлвийн тайлбар.
[Screenshot]
## A5. Оролт
Команд (≤1000 тэмдэгт). Дэмжих: энгийн команд, `|`, `<`, `>`, `&` (төгсгөлд), `cd`, `history`, `!!`, `exit`.
## A6. Ажиллуулах, зогсоох, reset
Команд бичээд Enter эсвэл Run. **Reset** — shell-ийг шинээр эхлүүлж терминалыг цэвэрлэнэ. Серверийг Ctrl+C-ээр зогсооно. Терминалаас шууд: `./osh` (гарах: `exit`).
## A7. Өнгө, төлөв
| Төлөв | Утга |
|---|---|
| running (шар) | процесс ажиллаж байна |
| zombie (ягаан) | дууссан, shell хараахан wait хийгээгүй |
| exited N (ногоон/улаан) | exit code N; 0 бол ногоон, бусад нь улаан |
| gone (саарал) | OS-оос арилсан, бүртгэлд exit байхгүй |
Командын дугаар `#N` нь тухайн session дахь дараалал.
## A8. Жишээ
**Жишээ 1 — pipe.** `echo hi | tr a-z A-Z | cat` → гаралт `HI`; модонд 3 процесс.
**Жишээ 2 — background ба zombie.** `sleep 3 &` → `[bg] pid ...`, мод дээр `running`; 3 секундын дараа `zombie`; дараагийн командын дараа `exited 0`.
**Жишээ 3 — session.** `cd /tmp` дараа нь `pwd` → `/tmp`.
**Жишээ 4 — redirection.** `echo data > /tmp/o.txt` дараа нь `cat < /tmp/o.txt` → `data`.
**Жишээ 5 — алдаа.** `nosuchcmd` → "No such file or directory", exit 127. `| ls` → syntax error.
## A9. Түгээмэл алдаа
| Асуудал | Шалтгаан | Шийдэл |
|---|---|---|
| `osh not built` | build хийгээгүй | `make` |
| `Address already in use` | 8765 порт завгүй | өмнөх серверийг зогсоо |
| `[хугацаа хэтэрлээ]` | команд 20 сек-ээс удаан | Reset дар |
| Хуудас шинэчлэгдэхгүй | сервер зогссон | `python3 ui/server.py` дахин ажиллуул |
| Windows-д ажиллахгүй | POSIX шаардлагатай | WSL ашигла |

# B. Operational заавар
## B1. Clone
`git clone [URL] && cd [REPO]`
## B2. Орчин
| Зүйл | Шаардлага | Шалгах |
|---|---|---|
| OS | Ubuntu 22.04/24 (туршсан), macOS | `uname -a` |
| Compiler | gcc (C11) эсвэл clang | `gcc --version` |
| Build | GNU make | `make --version` |
| Python | 3.8+ | `python3 --version` |
## B3. Dependency
Ubuntu: `sudo apt install -y build-essential python3`. macOS: `xcode-select --install`. Гадаад сан хэрэггүй.
## B4. Build ба Run
`make` · `./osh` · `python3 ui/server.py`
## B5. Үндсэн тест
`make test` → төгсгөлд `RESULT: 22 passed, 0 failed`. Тест: T01–T22 (Report 8.1).
## B6. Нэмэлт boundary/error тест
| Команд | Хүлээгдсэн |
|---|---|
| 3000 тэмдэгтийн мөр | `line too long` |
| `ls >` | `missing file name after redirection` |
| `\| ls` | `syntax error near '\|'` |
| `cat < байхгүй_файл` | `No such file or directory` |
| 17 шатлалтай pipe | `too many pipe stages` |
| `sleep 1 & ls` | `'&' must be last` |
## B7. Хүлээгдсэн үр дүн
Build анхааруулгагүй; `make test` 22/22; UI-д процесс бүр PID-тай гарна.
## B8. Known issues
Хашилт, wildcard, `$VAR`, `>>`, `2>`, `!n` байхгүй. UI автомат тестгүй. Background-ийн exit нь дараагийн команд өгөх үед бүртгэгдэнэ. Windows-д native ажиллахгүй.
