# IV-2-1 — UNIX Shell (osh)

F.CSM302 Үйлдлийн систем · Бие даалт 1 · Operating System Concepts (10th ed.), 3-р бүлэг, Programming Project 1.

**Зорилго:** C хэл дээр UNIX shell (`osh`) бичиж, процесс үүсгэх (fork/exec/wait), history, background, redirection, pipe-ийг хэрэгжүүлэх. Browser UI нь тухайн shell-ийн бодит процессуудыг PID-тай нь мод хэлбэрээр харуулна.

## Боломжууд
- `fork` / `execvp` / `waitpid`; `&` background; `history`, `!!`
- `<` `>` redirection; `|` pipe (16 шатлал хүртэл)
- `cd`, `exit` (shell-ийн дотоод команд)
- Нэг тасралтгүй session (UI-д `cd` хадгалагдана)
- Process tree: PID, команд, төлөв (running / zombie / exited / gone)

## Quick Start
Шаардлага: Linux эсвэл macOS, `gcc` (C11), `make`, Python 3. Windows-д WSL.
```
git clone <REPO-URL> && cd <REPO>
make            # osh бүтээнэ
make test       # 22 автомат тест
./osh           # терминалд шууд ажиллуулах
python3 ui/server.py   # дараа нь Chrome-оор http://127.0.0.1:8765
```
`ui/server.py` нь бодит shell команд ажиллуулдаг тул зөвхөн өөрийн компьютер дээр ашиглана.

## Бүтэц
```
src/osh.c        shell
ui/server.py     локал сервер (нэг osh session барьна)
ui/index.html    UI (терминал, process tree, history)
tests/run_tests.sh   автомат тест
docs/            Report, Manual
```

## AI болон бэлэн код
- AI: Claude (Anthropic) — [ГИШҮҮД ЭНД ЯГ ЮУНД АШИГЛАСНАА БИЧНЭ: код, тест, тайлангийн ноорог гэх мэт]. Гарсан кодыг багийн гишүүд уншиж, туршиж, засварласан.
- Гадаад сан ашиглаагүй (зөвхөн C стандарт сан, POSIX, Python стандарт сан).

## Баг
IV-2-1: [нэр, ID — гишүүн бүр]
