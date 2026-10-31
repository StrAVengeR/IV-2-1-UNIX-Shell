/* osh - UNIX Shell (OSC 10th ed., Ch.3 Programming Project 1)
 * Features: fork/exec, '&' background, history + '!!', '<' '>' redirection,
 * '|' pipes (any number of stages). Optional event log (JSON lines) for the
 * process-tree UI: set OSH_LOG=/path/file.jsonl                          */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <time.h>
#include <sys/wait.h>

#define MAX_LINE   1024
#define MAX_ARGS   64
#define MAX_STAGES 16
#define MAX_HIST   100
#define MAX_JOBS   64

typedef struct { char *argv[MAX_ARGS]; int argc; char *in, *out; } Stage;
typedef struct { pid_t pid; char cmd[128]; } Job;

static char  hist[MAX_HIST][MAX_LINE];
static int   hist_n = 0;
static Job   jobs[MAX_JOBS];
static int   log_fd = -1;
static long  t0_ms;
static int   last_status = 0, cmd_seq = 0;
static char  cur_line[1024] = "";

static long now_ms(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

static void json_esc(char *dst, size_t cap, const char *src) {
    size_t j = 0;
    for (const char *p = src; *p && j + 3 < cap; p++) {
        if (*p == '"' || *p == '\\') dst[j++] = '\\';
        if ((unsigned char)*p >= 32) dst[j++] = *p;
    }
    dst[j] = 0;
}

static void log_event(const char *ev, pid_t pid, pid_t ppid, const char *cmd, int bg, int code) {
    if (log_fd < 0) return;
    char c[256], l[512], buf[1024];
    json_esc(c, sizeof c, cmd); json_esc(l, sizeof l, cur_line);
    int n = snprintf(buf, sizeof buf,
        "{\"t\":%ld,\"ev\":\"%s\",\"pid\":%d,\"ppid\":%d,\"cmd\":\"%s\",\"bg\":%d,\"code\":%d,\"seq\":%d,\"line\":\"%s\"}\n",
        now_ms() - t0_ms, ev, (int)pid, (int)ppid, c, bg, code, cmd_seq, l);
    if (n > 0 && write(log_fd, buf, n) < 0) { /* best-effort */ }
}

static void add_hist(const char *line) {
    if (hist_n == MAX_HIST) { memmove(hist[0], hist[1], (MAX_HIST - 1) * MAX_LINE); hist_n--; }
    strcpy(hist[hist_n++], line);
}

static void job_add(pid_t pid, const char *cmd) {
    for (int i = 0; i < MAX_JOBS; i++) if (!jobs[i].pid) {
        jobs[i].pid = pid; snprintf(jobs[i].cmd, sizeof jobs[i].cmd, "%s", cmd); return; }
}
static const char *job_take(pid_t pid) {
    static char c[128];
    for (int i = 0; i < MAX_JOBS; i++) if (jobs[i].pid == pid) {
        strcpy(c, jobs[i].cmd); jobs[i].pid = 0; return c; }
    return NULL;
}

static void reap_background(void) {
    int st; pid_t p;
    while ((p = waitpid(-1, &st, WNOHANG)) > 0) {
        const char *c = job_take(p);
        int code = WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st);
        log_event("exit", p, getpid(), c ? c : "?", 1, code);
        printf("[done] pid %d (%s) exit=%d\n", (int)p, c ? c : "?", code);
    }
}

/* Tokenizer: | < > & are separate tokens even without spaces. Tokens are
 * copied into a pool so no delimiter is overwritten. Returns stage count,
 * 0 for an empty line, -1 on syntax error (message printed). */
static char pool[MAX_LINE * 2];
static int parse(const char *line, Stage *st, int *bg) {
    int n = 0, expect = 0; size_t pl = 0; *bg = 0;
    memset(st, 0, sizeof(Stage) * MAX_STAGES);
    const char *p = line;
    while (*p) {
        while (*p == ' ' || *p == '\t' || *p == '\n') p++;
        if (!*p) break;
        const char *b = p;
        if (strchr("|<>&", *p)) p++;
        else while (*p && !strchr(" \t\n|<>&", *p)) p++;
        size_t len = p - b;
        char c = b[0];
        int special = (len == 1 && strchr("|<>&", c));
        if (special && c == '|') {
            if (expect || st[n].argc == 0) { fprintf(stderr, "osh: syntax error near '|'\n"); return -1; }
            if (++n >= MAX_STAGES) { fprintf(stderr, "osh: too many pipe stages (max %d)\n", MAX_STAGES); return -1; }
        } else if (special && (c == '<' || c == '>')) {
            if (expect) { fprintf(stderr, "osh: syntax error near '%c'\n", c); return -1; }
            expect = (c == '<') ? 1 : 2;
        } else if (special && c == '&') {
            *bg = 1;
        } else {
            if (*bg) { fprintf(stderr, "osh: '&' must be last\n"); return -1; }
            char *t = pool + pl; memcpy(t, b, len); t[len] = 0; pl += len + 1;
            if (expect == 1) st[n].in = t;
            else if (expect == 2) st[n].out = t;
            else {
                if (st[n].argc >= MAX_ARGS - 1) { fprintf(stderr, "osh: too many arguments\n"); return -1; }
                st[n].argv[st[n].argc++] = t;
            }
            expect = 0;
        }
    }
    if (expect) { fprintf(stderr, "osh: missing file name after redirection\n"); return -1; }
    if (st[n].argc == 0) {
        if (n == 0 && !*bg) return 0;
        fprintf(stderr, "osh: syntax error: empty command\n"); return -1;
    }
    return n + 1;
}

static int run(Stage *st, int n, int bg, const char *line) {
    pid_t pids[MAX_STAGES]; int prev = -1, fd[2];
    fflush(stdout);
    for (int i = 0; i < n; i++) {
        if (i < n - 1 && pipe(fd) < 0) { perror("pipe"); return 1; }
        pid_t pid = fork();
        if (pid < 0) { perror("fork"); return 1; }
        if (pid == 0) {
            if (prev != -1) { dup2(prev, 0); close(prev); }
            if (i < n - 1) { dup2(fd[1], 1); close(fd[0]); close(fd[1]); }
            if (st[i].in) {
                int f = open(st[i].in, O_RDONLY);
                if (f < 0) { fprintf(stderr, "osh: %s: %s\n", st[i].in, strerror(errno)); _exit(1); }
                dup2(f, 0); close(f);
            }
            if (st[i].out) {
                int f = open(st[i].out, O_WRONLY | O_CREAT | O_TRUNC, 0644);
                if (f < 0) { fprintf(stderr, "osh: %s: %s\n", st[i].out, strerror(errno)); _exit(1); }
                dup2(f, 1); close(f);
            }
            execvp(st[i].argv[0], st[i].argv);
            fprintf(stderr, "osh: %s: %s\n", st[i].argv[0], strerror(errno));
            _exit(127);
        }
        pids[i] = pid;
        char c[128]; snprintf(c, sizeof c, "%s", st[i].argv[0]);
        log_event("spawn", pid, getpid(), c, bg, 0);
        if (prev != -1) close(prev);
        if (i < n - 1) { close(fd[1]); prev = fd[0]; }
    }
    for (int i = 0; i < n; i++) {
        if (bg) { job_add(pids[i], st[i].argv[0]); printf("[bg] pid %d\n", (int)pids[i]); }
        else {
            int s; waitpid(pids[i], &s, 0);
            int code = WIFEXITED(s) ? WEXITSTATUS(s) : 128 + WTERMSIG(s);
            log_event("exit", pids[i], getpid(), st[i].argv[0], 0, code);
            if (i == n - 1) last_status = code;
        }
    }
    (void)line; return 0;
}

int main(void) {
    t0_ms = now_ms();
    const char *lp = getenv("OSH_LOG");
    if (lp) log_fd = open(lp, O_WRONLY | O_CREAT | O_APPEND, 0644);
    log_event("shell", getpid(), getppid(), "osh", 0, 0);
    char line[MAX_LINE]; Stage st[MAX_STAGES];
    int tty = isatty(0), proto = getenv("OSH_PROTO") != NULL;
    if (proto) setvbuf(stdout, NULL, _IOLBF, 0);
    for (;;) {
        reap_background();
        if (proto) { printf("\x01READY %d\n", last_status); fflush(stdout); }
        else if (tty) { printf("osh> "); fflush(stdout); }
        if (!fgets(line, sizeof line, stdin)) break;
        if (!strchr(line, '\n') && !feof(stdin)) {
            fprintf(stderr, "osh: line too long (max %d)\n", MAX_LINE - 1);
            int ch; while ((ch = getchar()) != '\n' && ch != EOF); continue;
        }
        line[strcspn(line, "\n")] = 0;
        char *s = line; while (*s == ' ' || *s == '\t') s++;
        if (!*s) continue;
        if (!strcmp(s, "exit")) break;
        if (!strcmp(s, "!!")) {
            if (!hist_n) { printf("No commands in history.\n"); continue; }
            strcpy(line, hist[hist_n - 1]); s = line; printf("%s\n", s);
        }
        add_hist(s);
        cmd_seq++; snprintf(cur_line, sizeof cur_line, "%s", s); last_status = 0;
        if (!strcmp(s, "history")) {
            for (int i = hist_n - 1, k = 0; i >= 0 && k < 10; i--, k++) printf("%d %s\n", i + 1, hist[i]);
            continue;
        }
        int bg, n = parse(s, st, &bg);
        if (n <= 0) continue;
        if (!strcmp(st[0].argv[0], "cd") && n == 1) {
            const char *d = st[0].argc > 1 ? st[0].argv[1] : getenv("HOME");
            if (!d || chdir(d) < 0) fprintf(stderr, "osh: cd: %s\n", strerror(errno));
            continue;
        }
        run(st, n, bg, s);
    }
    reap_background();
    log_event("shell_exit", getpid(), getppid(), "osh", 0, 0);
    return 0;
}
