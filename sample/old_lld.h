#ifndef OLD_LLD_H
#define OLD_LLD_H

#include <stdint.h>

void dma_ctrl_start_set(uint32_t base, int value);
uint32_t dma_ctrl_start_get(uint32_t base);
void dma_ctrl_enable_set(uint32_t base, uint32_t value);
uint32_t dma_ctrl_enable_get(uint32_t base);
uint32_t dma_status_done_get(uint32_t base);

/* Customer manual declaration must remain untouched. */
int customer_private_debug_api(int level);

#endif /* OLD_LLD_H */
