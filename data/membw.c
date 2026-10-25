// membw: a bounded DRAM-bandwidth (or compute-only) load generator for contention experiments.
//
//   membw <threads> <seconds> <MB per array> <mode>
//     mode "read"  : each thread repeatedly reads two arrays (pure read traffic, like streaming weights)
//     mode "copy"  : each thread copies one array into another (read + write traffic)
//     mode "spin"  : register-only arithmetic, no memory traffic (control for CPU and power contention)
//
// Prints one line per second: "<elapsed_s> <GB/s>" where GB/s counts bytes read plus bytes written.
// Exits by itself after <seconds>. Threads run at utility QoS so the foreground processes keep priority.
#include <pthread/qos.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static atomic_int stop_flag;
static atomic_ullong bytes_total;
static int mode;            // 0 read, 1 copy, 2 spin
static size_t buf_bytes;

static void *worker(void *arg) {
    (void)arg;
    pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0);
    size_t n = buf_bytes / 8;
    uint64_t *a = NULL, *b = NULL;
    if (mode != 2) {
        a = malloc(buf_bytes); b = malloc(buf_bytes);
        if (!a || !b) { fprintf(stderr, "alloc failed\n"); return NULL; }
        for (size_t i = 0; i < n; i++) { a[i] = i * 7 + 1; b[i] = i * 3 + 2; }
    }
    uint64_t acc0 = 0, acc1 = 0, acc2 = 0, acc3 = 0;
    uint64_t x = (uint64_t)(uintptr_t)arg + 12345;
    while (!atomic_load(&stop_flag)) {
        if (mode == 0) {
            for (size_t i = 0; i + 3 < n; i += 4) { acc0 ^= a[i]; acc1 ^= a[i + 1]; acc2 ^= a[i + 2]; acc3 ^= a[i + 3]; }
            for (size_t i = 0; i + 3 < n; i += 4) { acc0 ^= b[i]; acc1 ^= b[i + 1]; acc2 ^= b[i + 2]; acc3 ^= b[i + 3]; }
            atomic_fetch_add(&bytes_total, 2 * buf_bytes);
        } else if (mode == 1) {
            for (size_t i = 0; i < n; i++) a[i] = b[i] + 1;
            for (size_t i = 0; i < n; i++) b[i] = a[i] + 1;
            atomic_fetch_add(&bytes_total, 4 * buf_bytes);
        } else {
            for (int k = 0; k < 20000000; k++) x = x * 6364136223846793005ULL + 1442695040888963407ULL;
        }
    }
    volatile uint64_t sink = acc0 ^ acc1 ^ acc2 ^ acc3 ^ x;
    (void)sink;
    return NULL;
}

int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: membw <threads> <seconds> <MB per array> <read|copy|spin>\n"); return 2; }
    int threads = atoi(argv[1]); double seconds = atof(argv[2]); buf_bytes = (size_t)atoi(argv[3]) * 1024 * 1024;
    mode = !strcmp(argv[4], "read") ? 0 : !strcmp(argv[4], "copy") ? 1 : 2;
    pthread_t th[64]; if (threads > 64) threads = 64;
    for (int i = 0; i < threads; i++) pthread_create(&th[i], NULL, worker, (void *)(uintptr_t)i);
    struct timespec t0; clock_gettime(CLOCK_MONOTONIC, &t0);
    unsigned long long last = 0; double lastt = 0, sum = 0; int cnt = 0;
    setvbuf(stdout, NULL, _IOLBF, 0);
    for (;;) {
        usleep(1000000);
        struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
        double el = (t.tv_sec - t0.tv_sec) + (t.tv_nsec - t0.tv_nsec) / 1e9;
        unsigned long long b = atomic_load(&bytes_total);
        double gbps = (b - last) / (el - lastt) / 1e9; last = b; lastt = el;
        printf("%.2f %.2f\n", el, gbps);
        if (el > 2.5) { sum += gbps; cnt++; }
        if (el >= seconds) break;
    }
    atomic_store(&stop_flag, 1);
    for (int i = 0; i < threads; i++) pthread_join(th[i], NULL);
    printf("mean %.2f\n", cnt ? sum / cnt : 0.0);
    return 0;
}
