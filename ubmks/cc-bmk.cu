/*  -*- mode: c++ -*-  */
#include "gg.h"
#include "ggcuda.h"
#include <cassert>

void kernel_sizing(CSRGraphTex &, dim3 &, dim3 &);
#define TB_SIZE 256

__global__ void kernel2(Worklist2 in_wl, Worklist2 out_wl)
{
  unsigned tid = TID_1D;
  unsigned nthreads = TOTAL_THREADS_1D;

  index_type wlnode_end;
  wlnode_end = *((in_wl).dindex);
  for (index_type wlnode = 0 + tid; wlnode < wlnode_end; wlnode += nthreads)
  {
    int node;
    bool pop;
    pop = (in_wl).pop_id(wlnode, node);
    if(pop) node += 10;
    (out_wl).push(node);
    next_1:
    ;
  }
}

__global__ void kernel2_coop(Worklist2 in_wl, Worklist2 out_wl)
{
  unsigned tid = TID_1D;
  unsigned nthreads = TOTAL_THREADS_1D;
  const int BLKSIZE = TB_SIZE;
  typedef cub::BlockScan<int, BLKSIZE> BlockScan;

  index_type wlnode_end;
  wlnode_end = roundup(*((in_wl).dindex), blockDim.x);
  for (index_type wlnode = 0 + tid; wlnode < wlnode_end; wlnode += nthreads)
  {
    int node;
    bool pop;
    pop = (in_wl).pop_id(wlnode, node);
    if(pop) node += 10;
    (out_wl).push_1item<BlockScan>(pop, node, TB_SIZE);
    next_1:
    ;
  }
}

__global__ void kernel2_gen(Worklist2 in_wl, Worklist2 out_wl)
{
  unsigned tid = TID_1D;
  unsigned nthreads = TOTAL_THREADS_1D;

  index_type wlnode_end;
  const int BLKSIZE = TB_SIZE;
  typedef cub::BlockScan<int, BLKSIZE> BlockScan;
  wlnode_end = roundup((*((in_wl).dindex)), (nthreads));
  for (index_type wlnode = 0 + tid; wlnode < wlnode_end; wlnode += nthreads)
  {
    int save_0_0;
    int node;
    bool pop;
    bool save_0_cond = false;
    pop = (in_wl).pop_id(wlnode, node);
    if(pop) {
      save_0_cond = true;
      save_0_0 = node + 10;
    }
    (out_wl).push_1item<BlockScan>(int(save_0_cond), (int) save_0_0, TB_SIZE);
    next_1:
    ;
  }
}


void check_wl(Worklist2& in, Worklist2& out) {
  int nsize = in.nitems();
  int diff = 10;

  assert(nsize == out.nitems());
  in.update_cpu();
  out.update_cpu();
  printf("checking %d items\n", nsize);
  printf("%d %d %d\n", 0, in.wl[0], out.wl[0]);
  for(int i = 0; i < nsize; i++) {
    if(in.wl[i] + diff != out.wl[i])
      printf("%d: %d %d\n", i, in.wl[i], out.wl[i]);

    assert(in.wl[i] + diff == out.wl[i]);
  }
}

int main(int argc, char ** argv)
{
  PipeContextT<Worklist2> wl;
  dim3 blocks (14*8);
  dim3 threads (TB_SIZE);
  int push =atoi(argv[1]);
  Timer t ("kernel2"), t2("kernel2_coop");
  cudaEvent_t st, en;
  float ms;

  check_cuda(cudaEventCreate(&st));
  check_cuda(cudaEventCreate(&en));
  
  //cudaFree(0);

  // the call below takes too much time on the CPU
  wl = PipeContextT<Worklist2>(push);
  wl.in_wl().update_gpu(push);
  while (wl.in_wl().nitems())
  {
    wl.out_wl().will_write();
    t.start();
    check_cuda(cudaEventRecord(st, 0));
    kernel2 <<<blocks, threads>>>(wl.in_wl(), wl.out_wl());
    check_cuda(cudaEventRecord(en, 0));
    check_cuda(cudaEventSynchronize(en));
    t.stop();

    check_cuda(cudaEventElapsedTime(&ms, st, en));

    printf("time (ign): %llu\n", t.duration());
    printf("time (ign): %f\n", ms);
    check_wl(wl.in_wl(), wl.out_wl());
    wl.advance();
    break;
  }
  
  t.reset();

  while (wl.in_wl().nitems())
  {
    wl.out_wl().will_write();
    t.start();
    kernel2 <<<blocks, threads>>>(wl.in_wl(), wl.out_wl());
    cudaDeviceSynchronize();
    t.stop();
    printf("time1: %llu\n", t.duration());
    check_wl(wl.in_wl(), wl.out_wl());
    wl.advance();
    break;
  }

  while (wl.in_wl().nitems())
  {
    wl.out_wl().will_write();
    t2.start();
    kernel2_coop <<<blocks, threads>>>(wl.in_wl(), wl.out_wl());
    cudaDeviceSynchronize();
    t2.stop();
    printf("time2: %llu\n", t2.duration());
    check_wl(wl.in_wl(), wl.out_wl());
    wl.advance();
    break;
  }

  t2.reset();

  while (wl.in_wl().nitems())
  {
    wl.out_wl().will_write();
    t2.start();
    kernel2_gen <<<blocks, threads>>>(wl.in_wl(), wl.out_wl());
    cudaDeviceSynchronize();
    t2.stop();
    printf("time3: %llu\n", t2.duration());
    check_wl(wl.in_wl(), wl.out_wl());
    wl.advance();
    break;
  }

}
