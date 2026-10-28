/* -*- mode: c++ -*- */
#include "gg.h"
#include "ggcuda.h"

#define TB_SIZE 256
typedef int edge_data_type;
typedef int node_data_type;
#define INF 10000

__global__ void count_kernel()
{
  unsigned tid = TID_1D;
  unsigned nthreads = TOTAL_THREADS_1D;

  const int BLKSIZE = TB_SIZE;
  typedef cub::BlockScan<multiple_sum<2, index_type>, BLKSIZE> BlockScan;
  const int ITSIZE = BLKSIZE * 1;
  typedef union np_shared<BlockScan::TempStorage, index_type, ITSIZE, TB_SIZE/32> npsTy;
  __shared__ npsTy nps;

  const int _NP_CROSSOVER_WP = 32;
  const int _NP_CROSSOVER_TB = TB_SIZE;

  multiple_sum<2, index_type> _np_mps;
  multiple_sum<2, index_type> _np_mps_total;

  struct NPInspector1 _np = {0,0,0,0,0,0};

  _np.size = threadIdx.x;
  _np.start = 0;

  _np_mps.el[0] = _np.size >= _NP_CROSSOVER_WP ? _np.size : 0;
  _np_mps.el[1] = _np.size < _NP_CROSSOVER_WP ? _np.size : 0;

  BlockScan(nps.temp_storage).ExclusiveSum(_np_mps, _np_mps, _np_mps_total);

  printf("%d %d %d\n", tid, _np_mps.el[0], _np_mps.el[1]);
}

int main(void) {
  count_kernel<<<1, 256>>>();
  cudaDeviceSynchronize();
}
