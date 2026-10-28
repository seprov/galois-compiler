/* -*- mode: C++ -*- */

#include "gg.h"

const char *prog_opts = "";
const char *prog_usage = "";
const char *prog_args_usage = "mis-nodes-list-file";

int *MIS_NODES;
int N_MIS_NODES;

extern int SKELAPP_RETVAL;

int process_prog_arg(int argc, char *argv[], int arg_start) {
  if(arg_start < argc) {
    FILE *f;

    f = fopen(argv[arg_start], "r");
    
    if(!f) {
      fprintf(stderr, "Unable to open file '%s' (err: %d, %s)\n", argv[arg_start], errno, strerror(errno));
      exit(EXIT_FAILURE);	
    }

    if(fscanf(f, "%d", &N_MIS_NODES) != 1) {
      fprintf(stderr, "Unable to read number of nodes\n");
      exit(EXIT_FAILURE);
    }

    assert(N_MIS_NODES > 0);

    MIS_NODES = (int *) malloc(N_MIS_NODES * sizeof(int));

    printf("Reading list of %d nodes from '%s' ...\n", N_MIS_NODES, argv[arg_start]);

    for(int i = 0; i < N_MIS_NODES; i++) {
      if(fscanf(f, "%d", &MIS_NODES[i]) != 1) {
	fprintf(stderr, "Error while reading nodes\n");
	exit(EXIT_FAILURE);
      } 
    }
    printf("Finished reading list.\n"); 

    fclose(f);

    return 1;
  }

  return 0;
}

void process_prog_opt(char c, char *optarg) {
  ;
}

void output(CSRGraphTy &g, const char *output_file) {
  FILE *f;

  bool not_independent = false, not_maximal = false;

  // TODO: should be done on GPU
  for(int i = 0; i < g.nnodes; i++) {
    if(g.node_data[i] == 2) not_independent = true;
    if(g.node_data[i] == 3) not_maximal = true;    

    if(not_independent && not_maximal) break;
  }

  // if it's not independent, maximal is don't care!
  printf("independent: %s, maximal: %s\n", not_independent ? "no" : "yes", not_maximal ? "no" : "yes");

  if(not_independent || not_maximal) 
    SKELAPP_RETVAL = 1;

  if(!output_file)
    return;

  if(strcmp(output_file, "-") == 0)
    f = stdout;
  else
    f = fopen(output_file, "w");

  for(int i = 0; i < g.nnodes; i++) {
    check_fprintf(f, "%d %d\n", i, g.node_data[i]);
  }
}
