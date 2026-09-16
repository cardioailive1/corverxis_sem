"""
Real GRPO training for SEM, targeting Qwen3.8-27B.

Honest scope note: the reward function (reward_functions.py) and dataset
construction (dataset.py) are genuinely tested — run them directly, no GPU
needed. This script's wiring of trl's GRPOTrainer/GRPOConfig uses their
real, current API (verified against trl's documentation, not guessed) —
but actually running this end to end requires a real GPU this environment
doesn't have, so that part is unverified by me. Review the config values
below before running for real, especially anything marked with a comment
explaining the reasoning, since they encode real judgment calls, not
arbitrary defaults.

Usage:
    python3 train_grpo.py --n-per-domain 200 --output-dir ./sem-checkpoint-v1
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dataset import build_hf_dataset
from reward_functions import sem_reward

BASE_MODEL = "Qwen/Qwen3.8-27B"


def build_model_and_tokenizer(base_model: str, use_4bit: bool):
    """QLoRA setup — 4-bit quantization + LoRA adapter. Necessary, not
    optional, at 27B scale: a 27B model needs ~56GB in bf16 (confirmed
    earlier in this project when Qwen3.8-27B was first selected), which
    won't fit on a single consumer/mid-tier GPU without quantization.
    4-bit quantization brings this down to a range that fits realistically
    on a single 48-80GB GPU alongside the activations GRPO's multi-sample
    generation needs."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant_config = BitsAndBytesConfig(
        load_in_4bit=use_4bit,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    ) if use_4bit else None

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=quant_config,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    if use_4bit:
        model = prepare_model_for_kbit_training(model)

    # LoRA config — rank 32 is a reasonable middle ground: high enough for
    # the adapter to actually capture "learn to propose structured causal
    # output" as a real behavioral shift, not so high that it approaches
    # full fine-tuning's memory cost. Matches the same lora_r used for
    # NexGen's own Pro tier training config, for consistency across this
    # project rather than picking a new number with no real basis.
    lora_config = LoraConfig(
        r=32, lora_alpha=64, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model, tokenizer


def register_checkpoint(backend_url: str, version: str, base_model: str, mean_reward: float, storage_key: str, training_run_id: str = None):
    """Calls the SEM+OSC backend's checkpoint registration route (added
    specifically to support this) once training produces something worth
    keeping. Never raises — a failed registration call shouldn't be able
    to make an otherwise-successful training run look like it failed."""
    import requests
    try:
        resp = requests.post(f"{backend_url}/api/checkpoints", json={
            "version": version, "base_model": base_model, "mean_reward": mean_reward,
            "storage_key": storage_key, "training_run_id": training_run_id,
        }, timeout=15)
        if resp.ok:
            print(f"Checkpoint registered: {resp.json()}")
        else:
            print(f"Checkpoint registration failed (training itself still succeeded): HTTP {resp.status_code} — {resp.text}")
    except Exception as e:
        print(f"Checkpoint registration failed (training itself still succeeded): {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default=BASE_MODEL)
    parser.add_argument("--n-per-domain", type=int, default=200, help="Training scenarios generated per domain — see design doc for why real training needs far more than the toy training_loop.py's --n_scenarios")
    parser.add_argument("--output-dir", default="./sem-checkpoint")
    parser.add_argument("--no-4bit", action="store_true", help="Disable 4-bit quantization — only realistic on a GPU with substantially more than 80GB VRAM")
    parser.add_argument("--num-generations", type=int, default=8, help="How many candidate completions GRPO samples per prompt — the 'group' in Group Relative Policy Optimization")
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--backend-url", default=os.environ.get("SEM_BACKEND_URL", "http://localhost:4001"))
    parser.add_argument("--register-checkpoint", action="store_true", help="POST the result to the SEM+OSC backend when training finishes")
    args = parser.parse_args()

    from trl import GRPOConfig, GRPOTrainer

    print(f"Building training dataset — {args.n_per_domain} scenarios × 6 domains = {args.n_per_domain * 6} total examples")
    train_dataset = build_hf_dataset(n_per_domain=args.n_per_domain)

    print(f"Loading {args.base_model} with QLoRA (4-bit: {not args.no_4bit})")
    model, tokenizer = build_model_and_tokenizer(args.base_model, use_4bit=not args.no_4bit)

    grpo_config = GRPOConfig(
        output_dir=args.output_dir,
        num_generations=args.num_generations,
        learning_rate=args.learning_rate,
        # scale_rewards="group" is GRPO's actual namesake behavior — reward
        # signal is normalized within each prompt's group of samples, not
        # against a global scale. Explicit here rather than relying on the
        # library default, since this is the one setting that most defines
        # "this is actually GRPO" as opposed to a generic PPO variant.
        scale_rewards="group",
        bf16=True,
        logging_steps=10,
        save_strategy="steps",
        save_steps=100,
    )

    trainer = GRPOTrainer(
        model=model,
        reward_funcs=[sem_reward],
        args=grpo_config,
        train_dataset=train_dataset,
        processing_class=tokenizer,
    )

    print("Starting GRPO training...")
    trainer.train()

    trainer.save_model(args.output_dir)
    print(f"Training complete. Adapter saved to {args.output_dir}")

    if args.register_checkpoint:
        # mean_reward here would realistically come from evaluating a
        # held-out scenario set post-training, not training-set reward —
        # left as a manual step / TODO rather than faked with a plausible
        # number, since a real eval harness doesn't exist yet.
        register_checkpoint(
            backend_url=args.backend_url,
            version=f"sem-{args.base_model.split('/')[-1]}-{os.path.basename(args.output_dir)}",
            base_model=args.base_model,
            mean_reward=None,
            storage_key=args.output_dir,
        )


if __name__ == "__main__":
    main()
