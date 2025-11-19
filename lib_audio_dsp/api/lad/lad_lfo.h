#pragma once

#include <stdint.h>

typedef struct 
{
    int32_t amplitude;
    uint32_t phase_incr; 
    float fs; 
} lad_lfo_ll_t;

typedef struct 
{
    uint32_t phase_acc;
} lad_lfo_state_t;

void lad_lfo_hl_to_ll(
    lad_lfo_ll_t *ll, 
    stage_params_hl_t hl, 
);

lad_lfo_state_t lad_lfo_init(
    lad_lfo_ll_t *ll,
    lad_lfo_state_t *state
);

void lad_lfo_update(
    lad_lfo_ll_t *ll,
    lad_lfo_state_t *state
);

void lad_lfo_process(
    lad_lfo_ll_t *ll,
    lad_lfo_state_t *state
);
