#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/vla-uv-cache}"
export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-$PWD/.python}"
if [ ! -x .venv-libero/bin/python ]; then
  uv venv --python 3.10 .venv-libero
fi
mkdir -p vendor
if [ ! -d vendor/LIBERO ]; then
  git clone --depth 1 https://github.com/Lifelong-Robot-Learning/LIBERO.git vendor/LIBERO
fi
uv pip install --python .venv-libero/bin/python \
  'numpy<2' 'robosuite==1.4.1' 'mujoco==3.2.3' \
  bddl easydict cloudpickle 'gym==0.25.2' 'imageio[ffmpeg]' \
  matplotlib h5py pyyaml tqdm einops
# CPU-only torch reads LIBERO's supplied initial states. No policy weights.
uv pip install --python .venv-libero/bin/python 'torch==2.14.1' \
  --index-url https://download.pytorch.org/whl/cpu
MUJOCO_GL=glfw .venv-libero/bin/python scripts/check_local_libero.py
