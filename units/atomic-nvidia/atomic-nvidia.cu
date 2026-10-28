/* -*- mode: c++ -*- */
#include <stdio.h>
#include <cuda.h>
#include <assert.h>

/* Based on ``Understanding and Using Atomic Memory Operations''
   Lars Nyland & Stephen Jones, NVIDIA
   GTC 2013

   Slide 60.
*/



const int UNLOCKED = 0;
const int LOCKED = 1;

__device__ bool elect_one_thread(int *lock) {
  return atomicCAS(lock, UNLOCKED, LOCKED) == UNLOCKED;
}

__device__ void unlock(int *lock) {
  int ret = atomicCAS(lock, LOCKED, UNLOCKED);
  assert(ret == LOCKED);
}

/* Definite compiler bug, causes branch divergence stack overflow
   because of incorrect position of SSY and BRA */
__global__ void test_hwstack_overflow(int *lock, int *count)
{
  bool done = 0;
  while(!done)
    {
      // Returns "true" for only
      // one active thread in warp
      
      if(done = elect_one_thread(lock)) {
	*count += threadIdx.x;
	unlock(lock);
      }
    } 
 }

/* Evaluation function for other workarounds */
__global__ void test_workaround_tries(int *lock, int *count)
{
  int done = 0;
  while(!done)
    {
      // Returns "true" for only
      // one active thread in warp
     
      done = threadIdx.x + ((int) elect_one_thread(lock));
 
      if(done == threadIdx.x + 1) {
	*count += threadIdx.x;
	unlock(lock);
	done = 1;
      } else {
	done = 0;
      }
    } 
 }

/* workaround suggested by NVIDIA */
__global__ void test_volatile(int *lock, int *count)
{
  volatile bool done = 0;
  while(!done)
    {
      // Returns "true" for only
      // one active thread in warp
      
      if(elect_one_thread(lock)) {
	*count += threadIdx.x;
	unlock(lock);
	done = 1;
      }
    } 
 }

__global__ void test(int *lock, int *count)
{
  bool done = 0;
  while(!done)
    {
      // Returns "true" for only
      // one active thread in warp
      
      if(elect_one_thread(lock)) {
	*count += threadIdx.x;
	unlock(lock);
	done = 1;
      }
    } 
 }

int main(int argc, char *argv[]) {
  int *dlock, *dcount;
  int count;

  if(argc != 2) {
    fprintf(stderr, "Usage: %s [normal|volatile|hwstack]\n", argv[0]);
    exit(1);
  }

  fprintf(stderr, "Compiled with CUDA NVCC %d.%d.%d\n", __CUDACC_VER_MAJOR__, __CUDACC_VER_MINOR__, __CUDACC_VER_BUILD__);

  assert(cudaMalloc(&dlock, 1*sizeof(int)) == cudaSuccess);
  assert(cudaMalloc(&dcount, 1*sizeof(int)) == cudaSuccess);

  assert(cudaMemset(dlock, 0, sizeof(int)) == cudaSuccess);
  assert(cudaMemset(dcount, 0, sizeof(int)) == cudaSuccess);

  const char *opt = argv[1];

  if(strcmp(opt, "normal") == 0) {
    test<<<1, 32>>>(dlock, dcount);
  } else if(strcmp(opt, "volatile") == 0) {
    test_volatile<<<1, 32>>>(dlock, dcount);
  } else if(strcmp(opt, "hwstack") == 0) {
    /* hwstack overflow error visible only under cuda-memcheck 7.5? */
    /* only launch overflow in 8.0 */
    test_hwstack_overflow<<<1, 32>>>(dlock, dcount);
  } else {
    fprintf(stderr, "Unknown option '%s'\n", opt);
    exit(1);
  }

  cudaError_t lastErr;
  if((lastErr = cudaMemcpy(&count, dcount, 1 * sizeof(int), cudaMemcpyDeviceToHost)) != cudaSuccess) {
    fprintf(stderr, "Launch/Memcpy failed. Error code: %d, %s\n", lastErr, cudaGetErrorString(lastErr));
    exit(1);
  }
  
  printf("count: %d (should be: %d)\n", count, 32*31/2);
  return 0;
}
