/*  -*- mode: c++ -*-  */
#include <cuda.h>
#include <stdlib.h>
#include "sharedptr.h"

#define THREADS 256

#define check_cuda(x) check_cuda_actual((x), __LINE__, __FILE__)

void check_cuda_actual(cudaError_t x, int L, const char *f) {
  if(x != cudaSuccess) {
    fprintf(stderr, "%s:%d: cuda error %d (%s)\n", f, L, x, cudaGetErrorString(x));
  }
  assert(x == cudaSuccess);
}

__global__ void test_atomic_tput(int * y, int * x, int limit)
{
  unsigned tid = threadIdx.x + blockIdx.x * blockDim.x ;
  unsigned nthreads = gridDim.x * blockDim.x;
  int prev = 1;
  
  for(int i = tid; i < limit; i+=nthreads)
  {
    int dst = x[i];
    prev = atomicAdd(y + dst, prev);
    if(prev == 0) prev = 1;
  }
}

void prep_x_1(int *x, int N) {
  memset(x, 0, N*sizeof(int));
}

void prep_x_2(int *x, int N) {

  for(int i = 0; i < N; i++) {
    x[i] = i;
  }
}

void prep_x_3(int *x, int N) {
  prep_x_2(x, N);
  int pull;

  for(int i = N-1; i >= 0; i--) {
    pull = random() % (i + 1);
    int tmp;

    tmp = x[i];
    x[i] = x[pull];
    x[pull] = tmp;
  }
}

int main(int argc, char *argv[])
{
  int BLOCKS = atoi(argv[2]);
  int ATOMICS = atoi(argv[1]);
  int OPS = ATOMICS;
  int TYPE = atoi(argv[3]);

  Shared<int> y (ATOMICS);
  Shared<int> x (ATOMICS);
  int * z ;
  dim3 blocks (BLOCKS);
  dim3 threads (THREADS);
  cudaEvent_t ev_start, ev_end;

  cudaDeviceProp cdp;

  if(cudaGetDeviceProperties(&cdp, 0) == cudaSuccess) {
    printf("%s (%d SMs)\n", cdp.name, cdp.multiProcessorCount);
  }

  switch(TYPE) {
  case 1:
    prep_x_1(x.cpu_wr_ptr(), ATOMICS);
    break;
  case 2:
    prep_x_2(x.cpu_wr_ptr(), ATOMICS);
    break;
  case 3:
    prep_x_3(x.cpu_wr_ptr(), ATOMICS);
    break;
  default:
    fprintf(stderr, "Unknown type %d\n", TYPE);
    exit(1);
  }
  printf("TYPE: %d\n", TYPE);

  if(false) {
  for(int i = 0; i < ATOMICS; i++) {
    printf("%d %d\n", i, x.cpu_rd_ptr()[i]);
  }

  exit(0);
  }
  y.zero_gpu();

  check_cuda(cudaEventCreate(&ev_start, cudaEventDefault));
  check_cuda(cudaEventCreate(&ev_end, cudaEventDefault));

  x.gpu_rd_ptr();
  y.gpu_wr_ptr();

  check_cuda(cudaEventRecord(ev_start));
  test_atomic_tput <<<blocks, threads>>>(y.gpu_wr_ptr(), x.gpu_rd_ptr(), ATOMICS);
  check_cuda(cudaEventRecord(ev_end));
  check_cuda(cudaDeviceSynchronize());

  float ms;
  check_cuda(cudaEventElapsedTime(&ms, ev_start, ev_end));

  printf("%f %f %f %f\n", ms, OPS/ms, (1.0*OPS/BLOCKS)/ms, (1.0*OPS/cdp.multiProcessorCount)/ms);
}
