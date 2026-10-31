#pragma once
#include <cstddef>

extern "C" {

void resonator_process(
    const float *input,
    float *output,
    unsigned long long len,
    float a,
    float b,
    float c);

}
