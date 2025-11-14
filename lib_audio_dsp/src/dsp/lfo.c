
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <assert.h>

#include "dsp/adsp.h"

// Verify params
static inline void _adsp_lfo_assert(float fs, float frequency, float amplitude, float phase_offset)
{
    assert(frequency <= 100);
    assert(fs < 64000);
    assert(amplitude <= 1.0f);
    assert(frequency <(fs / 2));
    assert(phase_offset >= 0.0f &&(phase_offset <= (2.0f * M_PI)));
    assert(fs > 0.0f &&(frequency > 0.0f));
}

// LFO Init function
lfo_component_t adsp_lfo_init(
    float fs, 
    float frequency, 
    float amplitude, 
    float phase_offset)
{
    lfo_component_t lfo;

    // verify params
    _adsp_lfo_assert(fs, frequency, amplitude, phase_offset);

    // compute params
    const float TWO_PI = 6.2831855;
    const float denom_phase = UINT32_MAX / TWO_PI;
    const float denom_inc = UINT32_MAX / fs;
    float tmp_phase_acc = phase_offset * denom_phase;
    float tmp_phase_inc = frequency * denom_inc;

    // init them
    lfo.amplitude = amplitude * ((1 << Q_SIG) - 1);
    lfo.phase_incr = (uint32_t)(tmp_phase_inc);
    lfo.phase_acc = (uint32_t)tmp_phase_acc;
    return lfo;
}

int32_t adsp_lfo_process(lfo_component_t *module, int32_t in)
{
    // search the floor and ceiling of the lut, interpolate between them
    (void)in; // avoid unused warnings, compiler should be optimizing this out
    uint32_t lut_idx = module->phase_acc >> LFO_LUT_SHR;
    uint32_t frac = module->phase_acc & ((1U << LFO_LUT_SHR) - 1);
    int64_t frac_q27 = ((int64_t)frac) << (Q_SIG - LFO_LUT_SHR);
    int64_t y0 = lfo_sine_lut[lut_idx];
    int64_t y1 = lfo_sine_lut[(lut_idx + 1) & (LFO_LUT_SIZE - 1)];
    int64_t interp_q27 = y0 + ((y1 - y0) * frac_q27 >> Q_SIG); //TODO optimise this mult 
    int64_t product = interp_q27 * (int64_t)module->amplitude; //TODO optimise
    int32_t out = (int32_t)(product >> Q_SIG);
    // increment.phase_acc
    module->phase_acc += module->phase_incr;
    return out;
}
