// Copyright 2025 XMOS LIMITED.
// This Software is subject to the terms of the XMOS Public Licence: Version 1.
#pragma once

#include "dsp/adsp.h"
#include "dsp/lfo.h"
#include "bump_allocator.h"

typedef struct
{
    lfo_component_t * lfo_comp;
    int n_inputs;
    int n_outputs;
    int frame_size;
}lfo_state_t;

// this will be replaced with the generated  header from lad file
typedef struct {
    float frequency;
    float amplitude;
    float phase_offset;
    float fs;
}lfo_config_t;

#define LFO_STAGE_REQUIRED_MEMORY (1 * sizeof(volume_control_t))

void lfo_init(
    module_instance_t* instance, 
    adsp_bump_allocator_t* allocator, 
    uint8_t id, int n_inputs, int n_outputs, int frame_size
);

void lfo_process(
    int32_t **input, 
    int32_t **output, 
    void *app_data_state
);
