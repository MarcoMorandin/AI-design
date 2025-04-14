# GPU version
ARG CUDA_VERSION=11.8.0
FROM nvidia/cuda:${CUDA_VERSION}-cudnn8-devel-ubuntu22.04 as gpu
# Note: Set CUDA_VERSION at build time with --build-arg CUDA_VERSION=<version> (e.g., 12.1.0).
# Check your CUDA version with 'nvcc -V'.

RUN apt-get update
RUN apt-get install -y python3
RUN apt-get -y install python3-pip git
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu${CUDA_VERSION//./}
# Note: The above dynamically removes dots from CUDA_VERSION (e.g., 11.8.0 -> cu118) for PyTorch URL.

RUN mkdir workspace
WORKDIR /workspace

RUN pip3 install fastapi uvicorn[standard] fsspec[http]==2023.1.0
RUN git clone https://github.com/facebookresearch/nougat.git
WORKDIR /workspace/nougat

RUN python3 setup.py install

EXPOSE 8503

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8503"]

# CPU version
FROM ubuntu:22.04 as cpu

RUN apt-get update
RUN apt-get install -y python3
RUN apt-get -y install python3-pip git
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

RUN mkdir workspace
WORKDIR /workspace

RUN pip3 install fastapi uvicorn[standard] fsspec[http]==2023.1.0
RUN git clone https://github.com/facebookresearch/nougat.git
WORKDIR /workspace/nougat

RUN python3 setup.py install

EXPOSE 8503

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8503"]