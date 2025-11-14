#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>

#include <xcore/hwtimer.h>

#include "dsp/adsp.h"

#define ARR_SIZE (1<<16)
#define PARAMS_FORMAT "%f,%f,%f,%f,%u"   /* fs, frequency, amplitude, phase_offset, num_samples */

static void test_lfo(
    const char* input_file,
    const char* params_file,
    const char* output_file)
{
    float fs, frequency, amplitude, phase_offset;
    unsigned num_samples;
    int32_t arr[ARR_SIZE];

    FILE* pf = fopen(params_file, "r");
    FILE* out = fopen(output_file, "wb");
    assert(out && pf);

    size_t elems = fscanf(
        pf, PARAMS_FORMAT, &fs, &frequency, &amplitude, &phase_offset, &num_samples
    );
    assert(elems == 5);
    fclose(pf);

    // Initialize LFO
    lfo_params_t lfo = adsp_lfo_init(fs, frequency, amplitude, phase_offset);
    unsigned remaining = num_samples;
    unsigned offset = 0;

    while (remaining > 0) {
        unsigned chunk = remaining > ARR_SIZE ? ARR_SIZE : remaining;

        // Fill buffer
        for (unsigned i = 0; i < chunk; i++) {
            arr[i] = adsp_lfo_process(&lfo, 0);
        }

        // Write chunk
        size_t written = fwrite(arr, sizeof(int32_t), chunk, out);
        assert(written == chunk);

        remaining -= chunk;
        offset += chunk;
    }
    fclose(out);
}

int main(int argc, char* argv[])
{
    assert(argc == 4);
    const char* input_file  = argv[1];
    const char* params_file = argv[2];
    const char* output_file = argv[3];
    test_lfo(input_file, params_file, output_file);
    return 0;
}
 
