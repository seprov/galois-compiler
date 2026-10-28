#include "nested_copy.cuh"
#include <iostream>
#include <stdexcept>
#include <vector>
#define CHECK(x) do { if (!(x)) throw std::runtime_error(#x); } while (false)
#define CUDA(x) CHECK((x) == cudaSuccess)
int main() {
  for (int count : {1, 14, 31, 32, 33, 128}) {
    const int lengths[] = {0, 1, 7, 32, 127, 128, 129, 257};
    std::vector<int> sizes(count), output(count * 257, -1);
    std::vector<unsigned> masks(count);
    for (int p = 0; p < count; ++p) sizes[p] = count == 1 ? 257 : lengths[p % 8];
    int *ds, *dv; unsigned* dm;
    CUDA(cudaMalloc(&ds, count * sizeof(int)));
    CUDA(cudaMalloc(&dv, output.size() * sizeof(int)));
    CUDA(cudaMalloc(&dm, count * sizeof(unsigned)));
    CUDA(cudaMemcpy(ds, sizes.data(), count * sizeof(int), cudaMemcpyHostToDevice));
    CUDA(cudaMemcpy(dv, output.data(), output.size() * sizeof(int), cudaMemcpyHostToDevice));
    CUDA(cudaMemset(dm, 0, count * sizeof(unsigned)));
    nested_copy<<<(count + 31) / 32, 32>>>(ds, dv, dm, count);
    CUDA(cudaGetLastError()); CUDA(cudaDeviceSynchronize());
    CUDA(cudaMemcpy(output.data(), dv, output.size() * sizeof(int), cudaMemcpyDeviceToHost));
    CUDA(cudaMemcpy(masks.data(), dm, count * sizeof(unsigned), cudaMemcpyDeviceToHost));
    for (int p = 0; p < count; ++p) {
      for (int i = 0; i < 257; ++i) CHECK(output[p * 257 + i] == (i < sizes[p] ? p * 1000 + i : -1));
      if (!sizes[p]) CHECK(masks[p] == 0);
      if (sizes[p] >= 32) CHECK(masks[p] == 0xffffffffu);
    }
    CUDA(cudaFree(ds)); CUDA(cudaFree(dv)); CUDA(cudaFree(dm));
  }
  std::cout << "IrGL generated nested work: values, bounds, partial blocks and 32-lane participation passed\n";
}
