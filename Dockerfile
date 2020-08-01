FROM python:3.6-slim
RUN apt-get update && \
    apt-get install -y libglib2.0-0 libsm6 libxrender1 libxext6 && \
    pip install opencv-python scikit-image imutils termcolor progressbar2
