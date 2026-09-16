# SEM GRPO training environment — meant for a dedicated, continuously-
# running GPU Pod, not RunPod Serverless. RL training runs live inference
# inside the training loop (generating multiple candidates per step, every
# step), which doesn't fit Serverless's cold-start-per-request model at
# all — see sem-training-architecture.md for the full reasoning.

FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

WORKDIR /app

COPY training/grpo/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY training/grpo/ ./grpo/
COPY training/simulators/ ./simulators/

WORKDIR /app/grpo

# No CMD — this is meant to be run interactively (SSH into the pod, run
# train_grpo.py with whatever arguments the specific run needs), not
# auto-started like a service. Matches the Pod-based pattern already
# proven reliable multiple times in this project, rather than trying to
# force this into a request/response container shape it doesn't fit.
