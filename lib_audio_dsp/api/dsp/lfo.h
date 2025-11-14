#include <stdint.h>

#ifndef Q_SIG
#define Q_SIG 27
#endif

#define LFO_LUT_BITS        (12)     /* 4096 points sine LUT, 16KB */
#define LFO_LUT_SIZE        (1 << LFO_LUT_BITS) 
#define LFO_LUT_SHR         (32 - LFO_LUT_BITS)
#define LFO_LUT_QSIG        (27)

extern const int32_t lfo_sine_lut[LFO_LUT_SIZE];

// Public
typedef struct 
{
    // PARAMETERS (set during init, fixed point)
    int32_t amplitude;          // initial amplitude in fixed point
    uint32_t phase_incr;        // phase increment per sample in fixed point
    // STATE (changes during processing)
    uint32_t phase_acc;         // current phase accumulator in fixed point
} lfo_component_t;

lfo_component_t adsp_lfo_init(
    float fs, 
    float frequency, 
    float amplitude, 
    float phase_offset
);

int32_t adsp_lfo_process(
    lfo_component_t *module, 
    int32_t in
);
