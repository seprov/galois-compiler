cmake_minimum_required(VERSION 3.22)
project(IrGLCompatibility LANGUAGES CXX CUDA)
include(CTest)
find_package(CUDAToolkit REQUIRED)
find_package(Python3 3.10 REQUIRED COMPONENTS Interpreter)
set(GALOIS_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../Galois" CACHE PATH "Galois fork containing irgl_nested.cuh")
set(IRGL_INCLUDE "${GALOIS_SOURCE_DIR}/libgpu/include")
# CUDA 13 places CUB under include/cccl; CUDA 12 uses include directly.
find_path(IRGL_CCCL_INCLUDE cub/block/block_scan.cuh
  HINTS ${CUDAToolkit_INCLUDE_DIRS} PATH_SUFFIXES cccl REQUIRED)
file(GLOB_RECURSE IRGL_COMPILER_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/../../src/*.py")
add_custom_command(OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/nested_copy.cuh"
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/../../tools/generate_nested.py"
    "${CMAKE_CURRENT_SOURCE_DIR}/nested_copy.py"
    --output "${CMAKE_CURRENT_BINARY_DIR}/nested_copy.cuh" --block-size 32
  DEPENDS ../../tools/generate_nested.py ../../src/ggc nested_copy.py ${IRGL_COMPILER_SOURCES} VERBATIM)
add_executable(irgl_nested_test nested_test.cu "${CMAKE_CURRENT_BINARY_DIR}/nested_copy.cuh")
target_include_directories(irgl_nested_test PRIVATE "${CMAKE_CURRENT_BINARY_DIR}" "${IRGL_INCLUDE}" "${IRGL_CCCL_INCLUDE}")
target_link_libraries(irgl_nested_test PRIVATE CUDA::cudart)
set_target_properties(irgl_nested_test PROPERTIES CUDA_STANDARD 17 CUDA_STANDARD_REQUIRED ON)
add_test(NAME irgl_nested_execution COMMAND irgl_nested_test)
set_tests_properties(irgl_nested_execution PROPERTIES TIMEOUT 30)
