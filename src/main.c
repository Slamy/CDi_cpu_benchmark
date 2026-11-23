
#include <errno.h>
#include <memory.h>
#include <module.h>
#include <signal.h>
#include <stdio.h>
#include <sysio.h>
#include <time.h>
#include <ucm.h>

#include "graphics.h"
#include "hwreg.h"
#include "irq.h"
#include "video.h"

#define SIG_BLANK 0x0100

int exit_app = 0;

int intHandler(sigCode)
int sigCode;
{
    if (sigCode == SIGINT) {
        printf("SIGINT!\n");
        exit_app = 1;
    } else if (sigCode == SIG_BLANK) {
        printf("Not expected!\n");
        dc_ssig(videoPath, SIG_BLANK, 0);
    }
}

void initProgram() {
    dc_wrli(videoPath, lctA, 0, 0, cp_cbnk(0));
    dc_wrli(videoPath, lctA, 0, 1, cp_clut(5, 0, 255, 0));

    dc_wrli(videoPath, lctA, 2, 0, cp_cbnk(0));
    dc_wrli(videoPath, lctA, 2, 1, cp_clut(5, 255, 0, 0));
    dc_wrli(videoPath, lctA, 2, 2, cp_nop());

    dc_wrli(videoPath, lctA, 279, 0, cp_cbnk(0));
    dc_wrli(videoPath, lctA, 279, 1, cp_clut(5, 255, 0, 255));
    dc_wrli(videoPath, lctA, 279, 2, cp_nop());

    dc_wrli(videoPath, lctA, 279 * 2, 0, cp_cbnk(0));
    dc_wrli(videoPath, lctA, 279 * 2, 1, cp_clut(5, 255, 0, 0));
    dc_wrli(videoPath, lctA, 279 * 2, 2, cp_nop());

    setIcf(ICF_MAX, ICF_MAX);
}

void initSystem() {
    intercept(intHandler);
    initVideo();
    initGraphics();
    initProgram();
}

void closeSystem() { closeVideo(); }

int number_a = 42;
int number_b = 100;
int number_c;
int opcnt_da1 = 0;
int opcnt_da0 = 0;

#define MCD212_CDSR1_DA 0x80

#define DVC

DrawmapDesc *dfg[2];
int btnsstate, ptx, pty;

char *sysram_buf = 0;
char *video1_buf = 0;
char *video2_buf = 0;
char *sysrom_mem = 0;
char *dvcrom_mem = 0;
struct sgtbuf timebuf;

/* Restore the system-wide trap vector on all explicit exit paths. */
void benchmark_exit(status) int status;
{
    irq_finish();
    exit(status);
}

void measure(location) char *location;
{
    int res;
    int irq_token;

    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        getime(&timebuf);
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        getime(&timebuf);
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] getime %d %d\n", location, opcnt_da0, opcnt_da1);
    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        res = getpid();
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        res = getpid();
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] getpid %d %d\n", location, opcnt_da0, opcnt_da1);
    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        res = pt_coord(videoPath, &btnsstate, &ptx, &pty);
        if (res)
            goto measurement_error;
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        res = pt_coord(videoPath, &btnsstate, &ptx, &pty);
        if (res)
            goto measurement_error;
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] pt_coord %d %d\n", location, opcnt_da0, opcnt_da1);
    /* ------------------------------------------------------------------ */

    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        res = dm_wrpix(videoPath, dfg[0]->dm_dnum, 50, 50, 10);
        if (res)
            goto measurement_error;
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        res = dm_wrpix(videoPath, dfg[0]->dm_dnum, 51, 50, 10);
        if (res)
            goto measurement_error;
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] dm_wrpix %d %d\n", location, opcnt_da0, opcnt_da1);

    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        res = dr_circ(videoPath, dfg[0]->dm_dnum, 0, 50, 50, 5);
        if (res)
            goto measurement_error;
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        res = dr_circ(videoPath, dfg[0]->dm_dnum, 0, 50, 50, 5);
        if (res)
            goto measurement_error;
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] dr_circ %d %d\n", location, opcnt_da0, opcnt_da1);

    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        res = gc_ptn(videoPath, 0, 3, 16, 16, 0, "dfdfddfdffdsf");
        if (res)
            goto measurement_error;
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        res = gc_ptn(videoPath, 0, 3, 16, 16, 0, "dfdfddfdffdsf");
        if (res)
            goto measurement_error;
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] gc_ptn %d %d\n", location, opcnt_da0, opcnt_da1);
    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        res = dc_wrli(videoPath, lctB, 0, 7, cp_icf(PB, curIcfB));
        if (res)
            goto measurement_error;
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        res = dc_wrli(videoPath, lctB, 0, 7, cp_icf(PB, curIcfB));
        if (res)
            goto measurement_error;
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] dc_wrli %d %d\n", location, opcnt_da0, opcnt_da1);
    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        number_c = number_a * number_b;
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        number_c = number_a * number_b;
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] Multi %d %d\n", location, opcnt_da0, opcnt_da1);
    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        number_c = number_a + number_b;
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        number_c = number_a + number_b;
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] Add %d %d\n", location, opcnt_da0, opcnt_da1);

    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        number_c = number_a / number_b;
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        number_c = number_a / number_b;
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] Div %d %d\n", location, opcnt_da0, opcnt_da1);

    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        video1_buf[opcnt_da0] = video2_buf[opcnt_da0];
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        video1_buf[opcnt_da1] = video2_buf[opcnt_da1];
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] Copy VRAM to VRAM %d %d\n", location, opcnt_da0, opcnt_da1);

#ifdef DVC
    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        sysram_buf[opcnt_da0] = video2_buf[opcnt_da0];
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        sysram_buf[opcnt_da1] = video2_buf[opcnt_da1];
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] Copy VRAM to SYSRAM %d %d\n", location, opcnt_da0, opcnt_da1);

    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        video2_buf[opcnt_da0] = sysram_buf[opcnt_da0];
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        video2_buf[opcnt_da1] = sysram_buf[opcnt_da1];
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] Copy SYSRAM to VRAM %d %d\n", location, opcnt_da0, opcnt_da1);

    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        sysram_buf[opcnt_da0] = sysrom_mem[opcnt_da0];
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        sysram_buf[opcnt_da1] = sysrom_mem[opcnt_da1];
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] Copy SYSROM to SYSRAM %d %d\n", location, opcnt_da0, opcnt_da1);

    /* ------------------------------------------------------------------ */
    irq_token = irq_mask();
    opcnt_da0 = 0;
    opcnt_da1 = 0;
    /* Wait for the next falling edge, even if we arrive during DA=0. */
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0)
        ;
    while (MCD212_CSR1R & MCD212_CDSR1_DA)
        ;
    while ((MCD212_CSR1R & MCD212_CDSR1_DA) == 0) {
        sysram_buf[opcnt_da0] = dvcrom_mem[opcnt_da0];
        opcnt_da0++;
    }
    while (MCD212_CSR1R & MCD212_CDSR1_DA) {
        sysram_buf[opcnt_da1] = dvcrom_mem[opcnt_da1];
        opcnt_da1++;
    }
    irq_restore(irq_token);
    printf("[%s] Copy DVCROM to SYSRAM %d %d\n", location, opcnt_da0, opcnt_da1);
    printf("-----\n");
#endif

    return;

measurement_error:
    irq_restore(irq_token);
    printf("Measurement failed: %d\n", res);
    benchmark_exit(1);

    /* An output of 94 804 on 210/05 seems plausible */
    /* The total tick count for one frame should be 900 at 50 Hz */
    /* 280 lines would be 808 ticks */
}

/* Linker-defined code symbol for the beginning of this module. */
extern void btext(void);

void runProgram() {
    char *module_base = (char *)btext;
    unsigned long module_size = ((struct modhcom *)module_base)->_msize;
    unsigned long measure_offset = (char *)measure - module_base;
    char *video_module = (char *)srqcmem(module_size, VIDEO1);
    char *dvc_module = (char *)srqcmem(module_size, SYSRAM);
    void (*measure_in_video_ram)(char *);
    void (*measure_in_dvc_ram)(char *);

    printf("Module size is %d\n", module_size);

    if (!dvc_module) {
        printf("Not enough DVC RAM\n");
        return;
    }

    if (!video_module) {
        printf("Not enough VIDEO RAM\n");
        return;
    }

    sysram_buf = (char *)srqcmem(8000, SYSRAM);
    video1_buf = (char *)srqcmem(8000, VIDEO1);
    video2_buf = (char *)srqcmem(8000, VIDEO2);
    sysrom_mem = (char *)0x400000;
    dvcrom_mem = (char *)0xe40000;

    if (!sysram_buf || !video1_buf || !video2_buf) {
        printf("Not enough  RAM\n");
        return;
    }

    /* Keep relative calls and code constants at their linked offsets.
     * Both copies continue to use the caller's original data area. */
    memcpy(video_module, module_base, module_size);
    memcpy(dvc_module, module_base, module_size);
    measure_in_video_ram = (void (*)(char *))(video_module + measure_offset);
    measure_in_dvc_ram = (void (*)(char *))(dvc_module + measure_offset);

    dc_ssig(videoPath, SIG_BLANK, 0);

    dfg[0] = dm_create(videoPath, PA, D_CLUT7, 768, 1140, 0, 0);
    dfg[1] = dm_create(videoPath, PB, D_CLUT7, 768, 1140, 0, 0);

    if (dfg[0] && dfg[1]) {
        int res, i;

        for (i = 0; i < 2; i++) {
            /* Set color register */
            res = dp_scr(videoPath, dfg[i]->dm_dnum, 0, 1);
            /* Draw a circle */
            res = dr_circ(videoPath, dfg[i]->dm_dnum, 0, 50, 50, 10);
        }
    } else {
        printf("Unable to create drawmaps: %d\n", errno);
        return;
    }

    while (!exit_app) {
        measure_in_video_ram("VIDEO1");
        measure_in_dvc_ram("SYSRAM");

        /* flush stdout before next measure */
        fflush(stdout);
    }
}

int main() {
    int res;
    printf("Hallo!\r\n");
    res = irq_init();
    if (res) {
        printf("Cannot install trap #7 IRQ handler (%d)\n", res);
        benchmark_exit(1);
    }
    /* Verify the raw trap returns to user mode with the requested IPL. */
    res = irq_mask();
    if (res < 0) {
        printf("trap #7: cannot mask interrupts\n");
        benchmark_exit(1);
    }
    {
        int state = irq_state();
        if (irq_restore(res) < 0)
            benchmark_exit(1);
        if (state < 0 || (state & 0x2700) != 0x0700) {
            printf("trap #7: user-mode IRQ mask was not preserved\n");
            benchmark_exit(1);
        }
    }
    initSystem();
    runProgram();
    closeSystem();
    irq_finish();
    sleep(1);
    benchmark_exit(0);
}
