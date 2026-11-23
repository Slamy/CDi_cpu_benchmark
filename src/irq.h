#ifndef _BENCHMARK_IRQ_H
#define _BENCHMARK_IRQ_H

/* Reserve raw trap #7 for this benchmark and restore its original vector on exit.
 * irq_mask returns the previous SR.IPL bits; irq_restore accepts that token.
 * irq_state returns SR through the trap, without a privileged user instruction.
 * Mask/restore calls belong outside the timed loops.
 */
int irq_init();
int irq_mask();
int irq_restore(int);
int irq_state();
int irq_finish();

#endif
