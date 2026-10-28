/* -*- mode: c++ -*- */
#include <stdio.h>
#include <cuda.h>
#include <cub/cub.cuh>
#include <cassert>

const int TB_SIZE = 256;

class Any {
 public:
  int *rv;
  int local;
  __device__ void thread_entry() { local = 0;}

  template <typename T>
  // the bug is that temp_storage should be a reference!
  __device__ void thread_exit(typename T::TempStorage temp_storage) { 
    local = T(temp_storage).Sum(local);

    if(threadIdx.x == 0 && local)  {
      printf("\n%d %d %d\n", blockIdx.x, threadIdx.x, local);
      *rv = local;
    }
  }

  __device__ void do_return(int value) { if(value) local = value;}
  __device__ void return_(int value) { if(value) *rv = value;}
};

__global__ void test(Any ret_val)
{
  typedef cub::BlockReduce<int, TB_SIZE> _br;
  __shared__ _br::TempStorage _ts;
  ret_val.thread_entry();

  ret_val.thread_exit<_br>(_ts);
}

__global__ void test2(Any ret_val)
{
  typedef cub::BlockReduce<int, TB_SIZE> _br;
  __shared__ _br::TempStorage _ts;
  int local = 0;
  local = _br(_ts).Sum(local);
  if(threadIdx.x == 0 && local) {
    *ret_val.rv = local;
  }
}

int main(void) {
  Any _rv;
  int r;

  assert(cudaMalloc(&_rv.rv, sizeof(int) * 1) == cudaSuccess);
  assert(cudaMemset(_rv.rv, 0, sizeof(int) * 1) == cudaSuccess);

  test<<<5, TB_SIZE>>>(_rv);
  assert(cudaMemcpy(&r, _rv.rv, sizeof(int) * 1, cudaMemcpyDeviceToHost) == cudaSuccess);

  printf("final: %d\n", r);
}
