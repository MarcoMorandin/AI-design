# GPU version
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04 as gpu

RUN apt-get update
RUN apt-get install -y python3
RUN apt-get -y install python3-pip git
RUN pip3 install torch torchvision torchaudio
# Note: The above dynamically removes dots from CUDA_VERSION (e.g., 11.8.0 -> cu118) for PyTorch URL.

RUN mkdir workspace
WORKDIR /workspace

RUN pip3 install fastapi uvicorn[standard] fsspec[http]==2023.5.0 python-multipart albumentations==1.3.0 transformers==4.36.0 "nougat-ocr[api]"
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

RUN pip3 install fastapi uvicorn[standard] fsspec[http]==2023.5.0 python-multipart albumentations==1.3.0 transformers==4.36.0 "nougat-ocr[api]"
RUN git clone https://github.com/facebookresearch/nougat.git
WORKDIR /workspace/nougat

RUN python3 setup.py install

EXPOSE 8503

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8503"]