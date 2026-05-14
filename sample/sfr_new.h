#ifndef DMA_SFR_H
#define DMA_SFR_H

#define DMA_CTRL_OFFSET              0x0000U
#define DMA_CTRL_START_MASK          0x00000002U
#define DMA_CTRL_START_SHIFT         1U
#define DMA_CTRL_ENABLE_MASK         0x00000004U
#define DMA_CTRL_ENABLE_SHIFT        2U

#define DMA_STATUS_OFFSET            0x0004U
#define DMA_STATUS_DONE_MASK         0x00000001U
#define DMA_STATUS_DONE_SHIFT        0U
#define DMA_STATUS_ERR_MASK          0x00000002U
#define DMA_STATUS_ERR_SHIFT         1U

#define TIMER_CFG_OFFSET             0x0000U
#define TIMER_CFG_MODE_MASK          0x00000003U
#define TIMER_CFG_MODE_SHIFT         0U

#endif
