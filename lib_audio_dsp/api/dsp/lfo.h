#include <stdint.h>

#define LUT_BITS 12         /* 4096 points sine LUT, 16KB */

// Public
typedef struct
{
    float fs;
    float frequency;
    float amplitude;
    float phase_offset;
} lfo_params_t;

lfo_params_t adsp_lfo_init(
    float fs, 
    float frequency, 
    float amplitude, 
    float phase_offset
);

int32_t adsp_lfo_process(
    lfo_params_t *module, 
    int32_t in
);
