/* -*- mode: c++ -*- */

#include <cuda.h>
#include <cassert>
#include "csr_graph.h"

__device__ __forceinline__
unsigned delay_fn(unsigned delay_clocks) {
  clock_t start = clock64();
  clock_t end;

  do {
    //x = gen_random(s1, s2, s3, s4);
    end = clock64();
  } while((end - start) < delay_clocks);

  return (end - start);
}

__launch_bounds__(256, 8)
__global__ void testfn(CSRGraphTex g, int *x, int *y, int *z, int delay_clocks) {
  unsigned tid = threadIdx.x + blockIdx.x * blockDim.x;
  unsigned nthreads = blockDim.x * gridDim.x;

  for(int i = tid; i < g.nnodes; i += nthreads) {
    int degree = g.getOutDegree(i);
    unsigned first_edge = g.getFirstEdge(i);
    int sum = 0;
    for(int j = 0; j < degree; j++) {
      int dst = g.getAbsDestination(first_edge++);
      sum += x[dst] + y[dst] + z[dst] ;//
    }
    //delay_fn(degree*delay_clocks);
    //g.node_data[i] = sum;
    g.edge_data[i] = sum;
  }
}

int main(int argc, char *argv[]) {
  int *dx, *dy, *dz;
  CSRGraphTex hg, gg;

  hg.readFromGR(argv[1]);
  hg.copy_to_gpu(gg);

  cudaMalloc(&dx, sizeof(int) * hg.nnodes);
  cudaMalloc(&dy, sizeof(int) * hg.nnodes);
  cudaMalloc(&dz, sizeof(int) * hg.nnodes);

  for(int i = 0; i < 1000; i+=250) {
    testfn<<<(hg.nnodes+255)/256, 256>>>(gg, dx, dy, dz, i);
    cudaDeviceSynchronize();

    testfn<<<15*16, 256>>>(gg, dx, dy, dz, i);
    cudaDeviceSynchronize();
  }
}
