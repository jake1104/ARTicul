#include "resonator.h"

void resonator_process(
    const float *input,
    float *output,
    unsigned long long len,
    float a,
    float b,
    float c) {
    float y1 = 0.0f;
    float y2 = 0.0f;
    for (unsigned long long i = 0; i < len; ++i) {
        float y = a * input[i] + b * y1 + c * y2;
        y2 = y1;
        y1 = y;
        output[i] = y;
    }
}
