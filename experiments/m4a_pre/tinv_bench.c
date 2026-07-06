/* T-inverse micro-benchmark: receive-side inverse of WR-ZipGuard layout transforms.
 *
 * Fresh C implementation, correctness-anchored to the unit-tested Python reference
 * (experiments/m1_6/layout.py) via golden vectors:
 *   forward chan    : view buffer as (rows, H) values, transpose -> (H, rows)
 *   forward bt      : SoA byte planes, plane 0 = byte0 (LE low byte), then plane 1
 *   forward chan_bt : bt(chan(buf))  =>  inverse = chan_inv(bt_inv(blob))
 *
 * Modes:
 *   verify <orig.bin> <transformed.bin> <dtype> <head_dim> <method>
 *   bench  <chunk_bytes> <head_dim> <dtype> <method> <threads> <seconds>
 *
 * dtype: bf16 (itemsize 2) | fp8 (itemsize 1); method: chan | chan_bt
 * Throughput is reported in ORIGINAL bytes per second (the decompressed stream the
 * inverse must keep up with). Thread model = multi-chunk parallelism: each thread
 * inverts its own private chunk (deployment: concurrent WRs), aggregate GB/s reported.
 */
#define _GNU_SOURCE
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define TILE 64

static double now_s(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

/* ---- inverse kernels ------------------------------------------------- */

/* bt inverse for itemsize 2: blob = [plane0 (n bytes) | plane1 (n bytes)]
 * -> interleaved values: out[2i] = plane0[i]; out[2i+1] = plane1[i]. */
static void bt_inv_2(const uint8_t *restrict in, uint8_t *restrict out, size_t n_values) {
    const uint8_t *p0 = in, *p1 = in + n_values;
    for (size_t i = 0; i < n_values; i++) {
        out[2 * i] = p0[i];
        out[2 * i + 1] = p1[i];
    }
}

/* chan inverse: in is (H, R) value-major, out is (R, H); cache-blocked transpose. */
static void chan_inv_u16(const uint16_t *restrict in, uint16_t *restrict out,
                         size_t rows, size_t H) {
    for (size_t rb = 0; rb < rows; rb += TILE)
        for (size_t cb = 0; cb < H; cb += TILE) {
            size_t rmax = rb + TILE < rows ? rb + TILE : rows;
            size_t cmax = cb + TILE < H ? cb + TILE : H;
            for (size_t r = rb; r < rmax; r++)
                for (size_t c = cb; c < cmax; c++)
                    out[r * H + c] = in[c * rows + r];
        }
}

static void chan_inv_u8(const uint8_t *restrict in, uint8_t *restrict out,
                        size_t rows, size_t H) {
    for (size_t rb = 0; rb < rows; rb += TILE)
        for (size_t cb = 0; cb < H; cb += TILE) {
            size_t rmax = rb + TILE < rows ? rb + TILE : rows;
            size_t cmax = cb + TILE < H ? cb + TILE : H;
            for (size_t r = rb; r < rmax; r++)
                for (size_t c = cb; c < cmax; c++)
                    out[r * H + c] = in[c * rows + r];
        }
}

/* Full inverse: blob -> original. tmp needed for chan_bt (bt_inv then chan_inv). */
static void invert(const uint8_t *in, uint8_t *out, uint8_t *tmp, size_t bytes,
                   size_t H, int itemsize, int with_bt) {
    size_t n_values = bytes / (size_t)itemsize;
    size_t rows = n_values / H;
    if (itemsize == 2) {
        if (with_bt) {
            bt_inv_2(in, tmp, n_values);
            chan_inv_u16((const uint16_t *)tmp, (uint16_t *)out, rows, H);
        } else {
            chan_inv_u16((const uint16_t *)in, (uint16_t *)out, rows, H);
        }
    } else {
        chan_inv_u8(in, out, rows, H); /* bt is identity for 1-byte dtypes */
    }
}

/* ---- verify mode ------------------------------------------------------ */

static uint8_t *read_file(const char *path, size_t *len) {
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *buf = malloc((size_t)sz);
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) { perror("fread"); exit(2); }
    fclose(f);
    *len = (size_t)sz;
    return buf;
}

static int run_verify(const char *orig_path, const char *trans_path, const char *dtype,
                      size_t H, const char *method) {
    size_t olen, tlen;
    uint8_t *orig = read_file(orig_path, &olen);
    uint8_t *trans = read_file(trans_path, &tlen);
    if (olen != tlen) { fprintf(stderr, "size mismatch %zu vs %zu\n", olen, tlen); return 1; }
    int itemsize = strcmp(dtype, "bf16") == 0 ? 2 : 1;
    int with_bt = strcmp(method, "chan_bt") == 0;
    uint8_t *out = malloc(olen), *tmp = malloc(olen);
    invert(trans, out, tmp, olen, H, itemsize, with_bt);
    int ok = memcmp(out, orig, olen) == 0;
    printf("{\"mode\":\"verify\",\"method\":\"%s\",\"dtype\":\"%s\",\"head_dim\":%zu,"
           "\"bytes\":%zu,\"bit_exact\":%s}\n",
           method, dtype, H, olen, ok ? "true" : "false");
    free(orig); free(trans); free(out); free(tmp);
    return ok ? 0 : 1;
}

/* ---- bench mode -------------------------------------------------------- */

typedef struct {
    size_t bytes, H;
    int itemsize, with_bt;
    double seconds;
    long iters;
    unsigned seed;
} job_t;

static void *worker(void *arg) {
    job_t *j = (job_t *)arg;
    uint8_t *in = malloc(j->bytes), *out = malloc(j->bytes), *tmp = malloc(j->bytes);
    unsigned s = j->seed;
    for (size_t i = 0; i < j->bytes; i++) { s = s * 1103515245u + 12345u; in[i] = (uint8_t)(s >> 16); }
    memset(out, 0, j->bytes);
    invert(in, out, tmp, j->bytes, j->H, j->itemsize, j->with_bt); /* warm */
    double t_end = now_s() + j->seconds;
    long iters = 0;
    while (now_s() < t_end) {
        invert(in, out, tmp, j->bytes, j->H, j->itemsize, j->with_bt);
        iters++;
    }
    j->iters = iters;
    free(in); free(out); free(tmp);
    return NULL;
}

static int run_bench(size_t bytes, size_t H, const char *dtype, const char *method,
                     int threads, double seconds) {
    int itemsize = strcmp(dtype, "bf16") == 0 ? 2 : 1;
    int with_bt = strcmp(method, "chan_bt") == 0;
    if (bytes % (H * (size_t)itemsize)) { fprintf(stderr, "unaligned chunk\n"); return 2; }
    pthread_t tid[256];
    job_t jobs[256];
    double t0 = now_s();
    for (int t = 0; t < threads; t++) {
        jobs[t] = (job_t){bytes, H, itemsize, with_bt, seconds, 0, 42u + (unsigned)t};
        pthread_create(&tid[t], NULL, worker, &jobs[t]);
    }
    long total_iters = 0;
    for (int t = 0; t < threads; t++) { pthread_join(tid[t], NULL); total_iters += jobs[t].iters; }
    double wall = now_s() - t0;
    double gbs = (double)total_iters * (double)bytes / wall / 1e9;
    printf("{\"mode\":\"bench\",\"method\":\"%s\",\"dtype\":\"%s\",\"chunk_bytes\":%zu,"
           "\"head_dim\":%zu,\"threads\":%d,\"iters\":%ld,\"wall_s\":%.3f,"
           "\"aggregate_GBps\":%.3f,\"per_thread_GBps\":%.3f}\n",
           method, dtype, bytes, H, threads, total_iters, wall, gbs, gbs / threads);
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 6 && strcmp(argv[1], "verify") == 0)
        return run_verify(argv[2], argv[3], argv[4], (size_t)atol(argv[5]), argv[6]);
    if (argc >= 8 && strcmp(argv[1], "bench") == 0)
        return run_bench((size_t)atol(argv[2]), (size_t)atol(argv[3]), argv[4], argv[5],
                         atoi(argv[6]), atof(argv[7]));
    fprintf(stderr,
            "usage: %s verify <orig> <transformed> <dtype> <head_dim> <method>\n"
            "       %s bench <chunk_bytes> <head_dim> <dtype> <method> <threads> <seconds>\n",
            argv[0], argv[0]);
    return 2;
}
