
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <assert.h>

#include "dsp/adsp.h"
#include "control/helpers.h"
#include "lfo_sine_lut_q27.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#ifndef Q_SIG
#define Q_SIG 27
#endif

// Internal globals
static struct
{
    uint32_t phase;                 
    uint32_t phase_acc;             
    int32_t *sine_lut_ptr;
    int32_t amplitude_q27;
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
    lfo_state.sine_lut_ptr = (int32_t *)lfo_sine_lut;

    // Precompute phase inc and offset
    const float TWO_PI = 6.2831855;
    const float denom_phase = UINT32_MAX / TWO_PI;
    const float denom_inc = UINT32_MAX / fs;
    float tmp_phase = phase_offset * denom_phase;
    float tmp_inc = frequency * denom_inc;
    lfo_state.phase = (uint32_t)tmp_phase;
    lfo_state.phase_acc = (uint32_t)(tmp_inc);
    lfo_state.amplitude_q27 = amplitude * ((1 << Q_SIG) - 1);
    return params;
}

int32_t adsp_lfo_process(lfo_params_t *module, int32_t in)
{
    // search the floor and ceiling of the lut, interpolate between them
    (void)in; (void)module; // avoid unused warnings, compiler should be optimizing this out
    uint32_t lut_idx = lfo_state.phase >> LFO_LUT_SHR;
    uint32_t frac = lfo_state.phase & ((1U << LFO_LUT_SHR) - 1);
    int64_t frac_q27 = ((int64_t)frac) << (Q_SIG - LFO_LUT_SHR);
    int64_t y0 = lfo_state.sine_lut_ptr[lut_idx];
    int64_t y1 = lfo_state.sine_lut_ptr[(lut_idx + 1) & (LFO_LUT_SIZE - 1)];
    int64_t interp_q27 = y0 + ((y1 - y0) * frac_q27 >> Q_SIG); //TODO optimise this mult 
    int64_t product = interp_q27 * (int64_t)lfo_state.amplitude_q27; //TODO optimise
    int32_t out = (int32_t)(product >> Q_SIG);
    // increment phase
    lfo_state.phase += lfo_state.phase_acc;
    return out;
}
