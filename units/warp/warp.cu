/* -*- mode: c++ -*- */
#include <stdio.h>
#include <cuda.h>
#include <assert.h>

/* 
   Test code replicating bug encountered in sssp-nf.
*/

__global__ void test(int *x) {
  int tid = threadIdx.x;

  int t = 0, f = 0;

  if(x[tid]) {
    unsigned int active = __ballot(1);
    t = __popc(active);
  } else {
    unsigned int active = __ballot(1);
    f = __popc(active);   
  }

  if(tid == 0) {
    printf("TEST:    true: %d\tfalse: %d\n", t, f);
  }  
}

__global__ void test_correct(int *x) {
  int tid = threadIdx.x;

  int t = 0, f = 0;

  if(x[tid]) {
    unsigned int active = __ballot(1);
    t = __popc(active);
  }

  if(tid == 0) {
    printf("CORRECT: true: %d\tfalse: %d\n", t, 32-t);
  }  
}


int main(void) {
  int *hx, *gx;

  fprintf(stderr, "Compiled with CUDA NVCC %d.%d.%d\n", __CUDACC_VER_MAJOR__, __CUDACC_VER_MINOR__, __CUDACC_VER_BUILD__);
  
  hx = (int *) calloc(32, sizeof(int));
  hx[0] = 1;

  assert(cudaMalloc(&gx, 32 * sizeof(int)) == cudaSuccess);
  assert(cudaMemcpy(gx, hx, 32 * sizeof(int), cudaMemcpyHostToDevice) == cudaSuccess);

  test<<<1, 32>>>(gx);
  test_correct<<<1, 32>>>(gx);

  assert(cudaDeviceSynchronize() == cudaSuccess);  
}
