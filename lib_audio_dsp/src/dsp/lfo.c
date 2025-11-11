
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <assert.h>

#include "dsp/adsp.h"
#include "control/helpers.h"

#define LUT_SIZE (1 << LUT_BITS)
#define LUT_SHR (32 - LUT_BITS)

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#ifndef Q_SIG
#define Q_SIG 27
#endif

/* TODO

    - to discuss LFO frequency and fs limits
    - to discuss amplitude limits
    - to dicuss the global state approachwith im not quite happy but is practical for now

    - there is no reset, control, etc... to improve
    - LUT resolution needs memory, about 16KB for 12bits which can be a lot. 
    Depending on frecuency we could have different LUT sizes to save memory.
    - currently only sine wave is supported 
    - there is no slew rate limiting on frequency or amplitude changes

*/

// Internal globals
static struct
{
    uint32_t phase;                 
    uint32_t phase_acc;             
    int32_t sine_lut[LUT_SIZE];
} lfo_state;

// Verify params
static inline void verify_lfo_params(
    lfo_params_t *params)
{
    assert(params->frequency <= 100);
    assert(params->fs < 64000);
    assert(params->amplitude <= 1.0f);
    assert(params->frequency < params->fs / 2);
    assert(params->phase_offset >= 0.0f && params->phase_offset <= (2.0f * M_PI));
    assert(params->fs > 0.0f && params->frequency > 0.0f);
}

// LFO Init function
lfo_params_t adsp_lfo_init(
    float fs, 
    float frequency, 
    float amplitude, 
    float phase_offset)
{
    // save parameters
    lfo_params_t params = { fs, frequency, amplitude, phase_offset };
    verify_lfo_params(&params);

    // Precompute LUT, phase, and phase increment
    const float TWO_PI = 2.0f * (float)M_PI;
    const float inv_lut_size = 1.0f / (float)LUT_SIZE;
    for (unsigned i = 0; i < LUT_SIZE; i++)
    {
        float angle = TWO_PI * ((float)i) * inv_lut_size;
        float tmp = (float)(amplitude * sinf(angle));
        lfo_state.sine_lut[i] = _float2fixed_saturate(tmp,  Q_SIG);
    }
    double tmp_phase = (double)((phase_offset * UINT32_MAX) / TWO_PI);
    double tmp_inc = (double)((frequency * UINT32_MAX) / fs);
    lfo_state.phase = (uint32_t)tmp_phase;
    lfo_state.phase_acc = (uint32_t)tmp_inc;
    return params;
}

// LFO processing
int32_t adsp_lfo_process(lfo_params_t *module, int32_t in)
{
    (void)in; (void)module; // avoid unused parameter warnings, compiler should optimize out
    uint32_t lut_idx = lfo_state.phase >> LUT_SHR;
    lfo_state.phase += lfo_state.phase_acc;
    int32_t out = lfo_state.sine_lut[lut_idx];
    return out;
}

int32_t adsp_lfo_process_interp(lfo_params_t *module, int32_t in)
{
    (void)in; (void)module; // avoid unused parameter warnings, compiler should optimize out
    uint32_t lut_idx = lfo_state.phase >> LUT_SHR;
    uint32_t frac = (lfo_state.phase & ((1U << LUT_SHR) - 1)) << 7; // Q27
    int32_t y0 = lfo_state.sine_lut[lut_idx];
    int32_t y1 = lfo_state.sine_lut[(lut_idx + 1) & (LUT_SIZE-1)];
    int32_t out = y0 + (int32_t)(((int64_t)(y1 - y0) * frac) >> 27);
    lfo_state.phase += lfo_state.phase_acc;
    return out;
}
