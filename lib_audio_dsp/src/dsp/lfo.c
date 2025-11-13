
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
    
    // Print intermediate values
    printf("\n========= C ==============\n");
    printf("frequency: %.8f\n", frequency);
    printf("fs: %.8f\n", fs);
    printf("TWO_PI: %.8f\n", TWO_PI);
    printf("denom_phase: %.8f\n", denom_phase);
    printf("denom_inc: %.8f\n", denom_inc);
    printf("tmp_phase: %.8f\n", tmp_phase);
    printf("tmp_inc: %.8f\n", tmp_inc);
    
    lfo_state.phase = (uint32_t)tmp_phase;
    lfo_state.phase_acc = (uint32_t)(tmp_inc);
    lfo_state.amplitude_q27 = (int32_t)(roundf(amplitude * ((1U << 27) - 1)));
    return params;
}

// LFO processing
int32_t adsp_lfo_process(lfo_params_t *module, int32_t in)
{
    (void)in; (void)module; // avoid unused parameter warnings
    uint32_t lut_idx = (lfo_state.phase + (1U << (LFO_LUT_SHR - 1))) >> LFO_LUT_SHR;
    int32_t lut_val_q27 = lfo_state.sine_lut_ptr[lut_idx];
    
    int64_t product = (int64_t)lut_val_q27 * (int64_t)(lfo_state.amplitude_q27); // Q27 * Q27 = Q54
    int32_t out = (int32_t)(product >> 27); // back to Q27
    
    // increment phase
    lfo_state.phase += lfo_state.phase_acc;
    return out;
}

int32_t adsp_lfo_process_interp(lfo_params_t *module, int32_t in)
{
    return 0;
}
