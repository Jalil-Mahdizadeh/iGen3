"""Generation loops shared by all iGen3 model variants."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import torch
from tqdm import tqdm

from .model import LoadedGenerator


@dataclass
class GenerationStats:
    requested: int
    generated: int
    seconds: float
    smiles_per_second: float
    batch_size: int
    output_path: Path
    batch_trace: list[dict[str, float | int]]


@torch.no_grad()
def top_k_mask_(logits: torch.Tensor, k: int | None) -> torch.Tensor:
    if not k or k >= logits.size(-1):
        return logits
    kth_vals = torch.topk(logits, int(k)).values[:, -1].unsqueeze(1)
    logits.masked_fill_(logits < kth_vals, torch.finfo(logits.dtype).min)
    return logits


def sample_next_token(
    logits: torch.Tensor,
    *,
    temperature: float,
    do_sample: bool,
    top_k: int | None,
) -> torch.Tensor:
    if top_k:
        top_k_mask_(logits, top_k)
    if not do_sample:
        return torch.argmax(logits, dim=-1)
    if temperature <= 0:
        raise ValueError("temperature must be > 0 when sampling")
    if temperature != 1.0:
        logits = logits / temperature
    gumbel_noise = torch.empty_like(logits).exponential_().log_().neg_()
    return torch.argmax(logits + gumbel_noise, dim=-1)


@torch.inference_mode()
def generate_de_novo_batch(
    generator: LoadedGenerator,
    batch_size: int,
    *,
    max_len: int | None = None,
    temperature: float = 1.0,
    do_sample: bool = True,
    top_k: int | None = 64,
) -> torch.Tensor:
    vocab = generator.vocab
    device = generator.device
    max_len = max_len or generator.spec.seq_len

    outputs = torch.full((batch_size, max_len), vocab.pad_idx, dtype=torch.long, device=device)
    outputs[:, 0] = vocab.sos_idx
    finished = torch.zeros(batch_size, dtype=torch.bool, device=device)
    k_caches, v_caches = generator.allocate_caches(batch_size, max_len)

    for pos in range(max_len - 1):
        logits = generator.model.step(outputs[:, pos], pos, k_caches, v_caches)
        next_tokens = sample_next_token(logits, temperature=temperature, do_sample=do_sample, top_k=top_k)
        next_tokens = torch.where(finished, torch.full_like(next_tokens, vocab.eos_idx), next_tokens)
        outputs[:, pos + 1] = next_tokens
        finished.logical_or_(next_tokens == vocab.eos_idx)
        if bool(finished.all()):
            break

    return outputs


def prepare_prefix_tensor(generator: LoadedGenerator, partial_smiles: list[str], max_len: int) -> tuple[torch.Tensor, torch.Tensor]:
    vocab = generator.vocab
    prefixes = [vocab.encode_smiles(smi, add_sos=True, strict=True)[:max_len] for smi in partial_smiles]
    prefix_tensor = torch.full((len(prefixes), max_len), vocab.pad_idx, dtype=torch.long, device=generator.device)
    prefix_lengths = torch.empty(len(prefixes), dtype=torch.long, device=generator.device)

    for row_index, prefix in enumerate(prefixes):
        if vocab.eos_idx in prefix:
            prefix = prefix[: prefix.index(vocab.eos_idx) + 1]
        length = min(len(prefix), max_len)
        prefix_lengths[row_index] = length
        prefix_tensor[row_index, :length] = torch.tensor(prefix[:length], dtype=torch.long, device=generator.device)

    return prefix_tensor, prefix_lengths


@torch.inference_mode()
def generate_partial_batch(
    generator: LoadedGenerator,
    partial_smiles: list[str],
    *,
    max_len: int | None = None,
    temperature: float = 1.0,
    do_sample: bool = True,
    top_k: int | None = 64,
) -> torch.Tensor:
    if not partial_smiles:
        raise ValueError("partial_smiles must contain at least one seed")

    vocab = generator.vocab
    device = generator.device
    max_len = max_len or generator.spec.seq_len
    batch_size = len(partial_smiles)
    prefix_tensor, prefix_lengths = prepare_prefix_tensor(generator, partial_smiles, max_len)

    outputs = torch.full((batch_size, max_len), vocab.pad_idx, dtype=torch.long, device=device)
    outputs[:, 0] = prefix_tensor[:, 0]
    finished = outputs[:, 0] == vocab.eos_idx
    k_caches, v_caches = generator.allocate_caches(batch_size, max_len)

    for pos in range(max_len - 1):
        logits = generator.model.step(outputs[:, pos], pos, k_caches, v_caches)
        next_pos = pos + 1
        forced_mask = prefix_lengths > next_pos

        if bool(forced_mask.all()):
            next_tokens = prefix_tensor[:, next_pos]
        else:
            sampled = sample_next_token(logits, temperature=temperature, do_sample=do_sample, top_k=top_k)
            next_tokens = torch.where(forced_mask, prefix_tensor[:, next_pos], sampled)

        next_tokens = torch.where(finished, torch.full_like(next_tokens, vocab.eos_idx), next_tokens)
        outputs[:, next_pos] = next_tokens
        finished.logical_or_(next_tokens == vocab.eos_idx)
        if bool(finished.all()):
            break

    return outputs


def decode_token_batch(generator: LoadedGenerator, token_batch: torch.Tensor) -> list[str]:
    arr = token_batch.detach().cpu().numpy()
    return generator.vocab.decode_rows(arr)


def write_token_batch(generator: LoadedGenerator, token_batch: torch.Tensor, fh) -> None:
    smiles = decode_token_batch(generator, token_batch)
    fh.write("\n".join(smiles))
    fh.write("\n")


def estimate_batch_upper_bound(generator: LoadedGenerator, max_batch_size: int, safety_fraction: float = 0.50) -> int:
    if generator.device.type != "cuda":
        return min(32, max_batch_size)
    free_bytes, _ = torch.cuda.mem_get_info(generator.device)
    bytes_per_value = torch.empty((), dtype=generator.dtype).element_size()
    kv_bytes_per_sequence = (
        2
        * generator.num_layers
        * generator.nhead
        * generator.spec.seq_len
        * generator.head_dim
        * bytes_per_value
    )
    if kv_bytes_per_sequence <= 0:
        return min(1, max_batch_size)
    estimated = int((free_bytes * safety_fraction) // kv_bytes_per_sequence)
    return max(1, min(max_batch_size, estimated))


def autotune_batch_size(generator: LoadedGenerator, *, max_batch_size: int = 32768, min_batch_size: int = 1) -> int:
    """Binary-search the largest batch size that fits a one-step cache allocation."""
    if generator.device.type != "cuda":
        return min(32, max_batch_size)

    upper = estimate_batch_upper_bound(generator, max_batch_size)
    lower = min_batch_size
    best = 0

    while lower <= upper:
        candidate = (lower + upper) // 2
        try:
            k_caches, v_caches = generator.allocate_caches(candidate, generator.spec.seq_len)
            last_tok = torch.full((candidate,), generator.vocab.sos_idx, dtype=torch.long, device=generator.device)
            _ = generator.model.step(last_tok, 0, k_caches, v_caches)
            del k_caches, v_caches, last_tok
            torch.cuda.empty_cache()
            best = candidate
            lower = candidate + 1
        except RuntimeError as exc:
            message = str(exc).lower()
            allocation_failure = (
                "out of memory" in message
                or "cudacachingallocator" in message
                or "internal assert failed" in message
            )
            if not allocation_failure:
                raise
            torch.cuda.empty_cache()
            upper = candidate - 1

    if best < min_batch_size:
        raise RuntimeError("Could not find a CUDA batch size that fits memory")
    return best


def decode_smiles_file(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def write_de_novo_file(
    generator: LoadedGenerator,
    *,
    output_path: Path,
    count: int,
    batch_size: int,
    temperature: float,
    do_sample: bool,
    top_k: int | None,
    progress: bool = True,
) -> GenerationStats:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    batches = math.ceil(count / batch_size)
    generated = 0
    start = perf_counter()

    iterator = range(batches)
    if progress:
        iterator = tqdm(iterator, desc=f"{generator.spec.model_id} de novo")

    with output_path.open("w", encoding="utf-8") as fh:
        batch_trace: list[dict[str, float | int]] = []
        for batch_index in iterator:
            current_bs = min(batch_size, count - generated)
            if current_bs <= 0:
                break
            tokens = generate_de_novo_batch(
                generator,
                current_bs,
                temperature=temperature,
                do_sample=do_sample,
                top_k=top_k,
            )
            write_token_batch(generator, tokens, fh)
            generated += current_bs
            elapsed = perf_counter() - start
            batch_trace.append(
                {
                    "batch_index": batch_index + 1,
                    "generated": generated,
                    "elapsed_seconds": elapsed,
                    "smiles_per_second": generated / max(elapsed, 1e-9),
                }
            )
            if progress and hasattr(iterator, "set_postfix"):
                iterator.set_postfix({"SMILES/s": f"{generated / max(elapsed, 1e-9):.1f}"})

    seconds = perf_counter() - start
    return GenerationStats(
        requested=count,
        generated=generated,
        seconds=seconds,
        smiles_per_second=generated / max(seconds, 1e-9),
        batch_size=batch_size,
        output_path=output_path,
        batch_trace=batch_trace,
    )


def expand_partial_seeds(seeds: list[str], samples_per_seed: int, count: int | None = None) -> list[str]:
    expanded = [seed for seed in seeds for _ in range(samples_per_seed)]
    if count is not None:
        expanded = expanded[:count]
    return expanded


def write_partial_file(
    generator: LoadedGenerator,
    *,
    seeds: list[str],
    output_path: Path,
    batch_size: int,
    samples_per_seed: int,
    count: int | None,
    temperature: float,
    do_sample: bool,
    top_k: int | None,
    progress: bool = True,
) -> GenerationStats:
    expanded = expand_partial_seeds(seeds, samples_per_seed, count)
    total = len(expanded)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    batches = math.ceil(total / batch_size)
    generated = 0
    start = perf_counter()

    iterator = range(batches)
    if progress:
        iterator = tqdm(iterator, desc=f"{generator.spec.model_id} partial")

    with output_path.open("w", encoding="utf-8") as fh:
        batch_trace: list[dict[str, float | int]] = []
        for batch_index in iterator:
            batch = expanded[batch_index * batch_size : (batch_index + 1) * batch_size]
            tokens = generate_partial_batch(
                generator,
                batch,
                temperature=temperature,
                do_sample=do_sample,
                top_k=top_k,
            )
            write_token_batch(generator, tokens, fh)
            generated += len(batch)
            elapsed = perf_counter() - start
            batch_trace.append(
                {
                    "batch_index": batch_index + 1,
                    "generated": generated,
                    "elapsed_seconds": elapsed,
                    "smiles_per_second": generated / max(elapsed, 1e-9),
                }
            )
            if progress and hasattr(iterator, "set_postfix"):
                iterator.set_postfix({"SMILES/s": f"{generated / max(elapsed, 1e-9):.1f}"})

    seconds = perf_counter() - start
    return GenerationStats(
        requested=total,
        generated=generated,
        seconds=seconds,
        smiles_per_second=generated / max(seconds, 1e-9),
        batch_size=batch_size,
        output_path=output_path,
        batch_trace=batch_trace,
    )


def line_count(path: Path) -> int:
    with path.open("rb") as fh:
        return sum(1 for _ in fh)


def quick_decode_preview(generator: LoadedGenerator, token_batch: torch.Tensor, limit: int = 5) -> list[str]:
    arr = token_batch.detach().cpu().numpy()
    return generator.vocab.decode_rows(arr[:limit])


def unique_fraction(smiles: list[str]) -> float:
    if not smiles:
        return 0.0
    return len(set(smiles)) / len(smiles)
