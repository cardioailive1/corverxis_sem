"""Load the base language model. Qwen3.8-27B is a native vision-language model, and its model card loads it with
AutoModelForMultimodalLM. Try the plain causal-LM class first (text-only training needs only the language side), and
fall back to the multimodal class if the checkpoint is not registered for it. NOT yet tested against the real 27B
checkpoint: run the small `--n-per-domain 20` test first, and report the error if loading fails."""
def load_language_model(base_model, **kwargs):
    import transformers
    errors = []
    for name in ("AutoModelForCausalLM", "AutoModelForMultimodalLM", "AutoModelForImageTextToText"):
        cls = getattr(transformers, name, None)
        if cls is None: continue
        try:
            model = cls.from_pretrained(base_model, **kwargs)
            print(f"Loaded {base_model} with {name}")
            return model
        except Exception as e:                      # noqa: BLE001 - try the next class, report all if none work
            errors.append(f"{name}: {type(e).__name__}: {str(e)[:200]}")
    raise RuntimeError("Could not load " + base_model + ". Tried:\n  " + "\n  ".join(errors))
