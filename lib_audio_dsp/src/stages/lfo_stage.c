// Copyright 2024-2025 XMOS LIMITED.
// This Software is subject to the terms of the XMOS Public Licence: Version 1.

#include <string.h>
#include <xcore/assert.h>

#include "stages/lfo_stage.h"


void lfo_init(
    module_instance_t* instance, 
    adsp_bump_allocator_t* allocator, 
    uint8_t id, int n_inputs, int n_outputs, int frame_size
)
{
    lfo_state_t *state = instance->state;
    lfo_config_t *config = instance->control.config;

    memset(state, 0, sizeof(lfo_state_t));
    state->n_inputs = n_inputs;
    state->n_outputs = n_outputs;
    state->frame_size = frame_size;
    xassert(n_inputs == 1 && "Adder should only have one output");

    state->lfo_comp = adsp_bump_allocator_malloc(allocator, LFO_STAGE_REQUIRED_MEMORY);
    state->lfo_comp[0] = adsp_lfo_init(
        config->fs, 
        config->frequency, 
        config->amplitude, 
        config->phase_offset
    );
}

void lfo_process(
    int32_t **input, 
    int32_t **output, 
    void *app_data_state
)
{
    lfo_state_t *state = app_data_state;
    for(unsigned idx = 0; idx < state->frame_size; idx++) {
        int32_t *out = &output[0][idx];
        *out = adsp_lfo_process(&state->lfo_comp[0], input[0][idx]);
    }
}
