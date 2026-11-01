# IV-2-1 — UNIX Shell (osh)

**F.CSM302 Үйлдлийн систем · Бие даалт 1 · Хуваарилалтын код: IV-2-1**
Operating System Concepts (10th ed.), 3-р бүлэг, Programming Project 1: UNIX Shell. UI дүрслэл: Process tree.

## Зорилго
C хэл дээр UNIX shell (`osh`) бичиж `fork`/`execvp`/`waitpid`, `&` background, `!!` ба `history`, `<` `>` redirection, `|` pipe-ийг хэрэгжүүлэх. Browser UI нь shell-ийн ажиллуулсан процессуудыг командаар нь бүлэглэж, бодит PID болон төлөвтэй нь (running, zombie, exited, gone) мод хэлбэрээр харуулна.

## Боломжууд
- `fork` / `execvp` / `waitpid`; `&` background; `!!`, `history` (сүүлийн 10)
- `<` `>` redirection; `|` pipe (16 шатлал хүртэл)
- `cd`, `exit` дотоод командууд
- Нэг тасралтгүй session (UI-д `cd` хадгалагдана)
- Буруу оролтод ойлгомжтой мэдээлэл: синтакс алдаа, байхгүй команд/файл, хэт урт мөр, хэт олон шатлал
- 22 автомат тест

## Quick Start
Шаардлага: Linux эсвэл macOS, `gcc` (C11), `make`, Python 3. Windows-д WSL2.
```
git clone https://github.com/StrAVengeR/IV-2-1-UNIX-Shell.git
cd IV-2-1-UNIX-Shell
make                    # osh бүтээнэ
make test               # 22 автомат тест (RESULT: 22 passed, 0 failed)
./osh                   # терминалд шууд
python3 ui/server.py    # UI: http://127.0.0.1:8765 (хөтчөөр нээнэ)
```
`ui/server.py` нь бодит shell команд ажиллуулдаг тул зөвхөн өөрийн компьютер дээр ашиглана.

Жишээ команд: `echo hi | tr a-z A-Z | cat`, `echo data > /tmp/o.txt`, `cat < /tmp/o.txt`, `sleep 5 &` (6–7 секунд хүлээвэл `zombie`), `!!`, `history`, `cd /tmp`, `nosuchcmd`.

## Бүтэц
```
README.md
Makefile
src/osh.c               shell
ui/server.py            локал сервер (нэг osh session барина)
ui/index.html           UI (терминал, process tree, history)
tests/run_tests.sh      22 автомат тест
tests/diag.sh           UI ажиллахгүй үед оношлох скрипт
docs/                   IV-2-1_BD1_Report.pdf, IV-2-1_Manual.pdf, images/
```

## Туршсан орчин
Xubuntu 25.10 (VirtualBox), Linux 6.17.0-5-generic x86_64, gcc 15.2.0, GNU Make 4.4.1, Python 3.13.7. macOS болон WSL2-д туршаагүй.

## Баримт бичиг
- Тайлан: `docs/IV-2-1_BD1_Report.pdf`
- Manual (хэрэглэгчийн ба operational заавар): `docs/IV-2-1_Manual.pdf`

## AI болон бэлэн код
- **AI:** Claude (Anthropic)-ийг эх код (`src/osh.c`, `ui/`), автомат тест, тайлан ба manual-ын ноорог бэлтгэхэд ашигласан. Багийн гишүүд кодыг уншиж, өөрсдийн компьютерт ажиллуулж, тест болон UI-г туршиж, тайланг шалгаж засварласан.
- **Бэлэн код, сан:** ашиглаагүй. Зөвхөн C стандарт сан, POSIX системийн дуудлага, Python стандарт сан.
- Нууц түлхүүр, нууц үг, хувийн өгөгдөл repository-д байхгүй.

## Баг IV-2-1
| Гишүүн | ID |
|---|---|
| Б. Билгүүн | B242270035 |
| Г. Анужин | B241940083 |
| Э. Чагдарсүрэн | B160910044 |
| Ц. Энх-Од | B231890017 |
| Г. Маралгуа | B210930821 |
| Т. Саруулзаяа | B232230057 |