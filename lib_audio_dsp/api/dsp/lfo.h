#include <stdint.h>


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

// -60 Db, 10cycles (default)
int32_t adsp_lfo_process(
    lfo_params_t *module, 
    int32_t in
);

// in progress, -80db, 20 cycles
int32_t adsp_lfo_process_interp(
    lfo_params_t *module, 
    int32_t in
);
