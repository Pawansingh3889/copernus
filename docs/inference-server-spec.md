# Copernus inference server: procurement spec

> **Doc ref:** COP-HW-01 · **Date:** 11 August 2026 · **Status:** for quotation
> **Context:** ARCHITECTURE.md §8 (on-prem model decision). One new box joins
> the estate as the eighth server. Everything the assistant sees stays on site.

## 1. Purpose

One machine that runs both assistant models locally: the workhorse
(`Qwen3.6-27B`) and the judge (`gpt-oss-20b`), served by vLLM behind an
OpenAI-compatible endpoint on the plant LAN. Sized for under ten concurrent
users. No pipeline traffic leaves site.

## 2. GPU options

| | Card | VRAM | Street (ex VAT) | Verdict |
|---|---|---|---|---|
| **A** | NVIDIA RTX PRO 5000 Blackwell | 48 GB GDDR7 ECC | ~£4,500 to 5,000 | **Recommended.** Both models resident at once (workhorse Q4 ~17 GB + judge ~13 GB) with KV-cache headroom. 300 W, dual-slot, active-cooled, fits a tower. |
| **B** | NVIDIA RTX PRO 6000 Blackwell | 96 GB GDDR7 ECC | ~£8,300 to 13,000 | Headroom variant: workhorse at FP8, long contexts, room for a bigger model if the Phase 9 eval demands one. Buy only if budget is easy. |

Rejected, so procurement is not sold them: **2× RTX 5090** (2026 street price
£5,700 to 7,000 *each*, no ECC, consumer warranty, dearer than A and worse) and
**RTX 6000 Ada** (older generation, slower memory, higher price than A).

## 3. System build (Option A)

Prefer an OEM tower workstation (Dell Precision, Lenovo ThinkStation, HP Z
class) with next-business-day on-site warranty over a self-build. The plant
has no resident IT; the warranty is the support plan.

| Component | Spec | Note |
|---|---|---|
| GPU | RTX PRO 5000 Blackwell 48 GB | ECC on |
| CPU | 12-16 cores (Xeon w5 / Ryzen 9 class) | Serving is GPU-bound; the CPU is not the bottleneck |
| RAM | 128 GB ECC DDR5 (96 GB floor) | DRAM prices are volatile in 2026; quote will move |
| Storage | 2× 2 TB NVMe, mirrored | Weights (~150 GB per model set), versioned corpus, logs |
| PSU | 850 W, 80 Plus Platinum | 300 W card + headroom |
| NIC | 1 GbE (10 GbE if the switch supports it) | Static IP on the app-server VLAN |
| UPS | 1,500 VA line-interactive | Plant power is compressor-heavy |
| OS | Ubuntu 24.04 LTS | vLLM needs Linux; podman for containers, as the rest of the repo |

## 4. Placement and rules

- Comms/office room only. The box is not IP-rated; washdown areas, cold
  rooms and condensation kill it.
- No internet route. Updates arrive via controlled temporary egress or an
  offline mirror, decided with the client's IT.
- Reachable only from the app-server VLAN.
- Never co-hosted on the production SQL box (C-01).

## 5. Acceptance checklist

Delivered means all of these are true, demonstrated on site:

- [ ] `nvidia-smi` clean, ECC enabled
- [ ] Both vLLM services answer OpenAI-compatible `/v1/chat/completions`
      (workhorse :8001, judge :8002)
- [ ] Workhorse ≥25 tok/s single stream; first token <2 s at an 8K prompt
- [ ] Guided decoding returns schema-valid JSON against the verifier's test schema
- [ ] Prefix caching enabled; corpus warm-load test passes
- [ ] No default route; unreachable from outside the app VLAN
- [ ] Full power-cycle: both services return with no hands on the box

## 6. Indicative budget (ex VAT, August 2026)

| | Total |
|---|---|
| Option A (48 GB card + OEM workstation + UPS) | **~£7,200 to 8,700** |
| Option B (96 GB card, same chassis) | ~£11,000 to 16,500 |

GPU and DRAM prices are moving weekly in the 2026 market. Treat vendor
quotes as valid for days, not weeks, and buy on an actual quote, not this
page.

## 7. Timing

The box must be live before real incident narratives flow (Phases 9 to 10).
Phase 8 corpus work and assistant development run on the Phase 3 synthetic
estate, which contains no personal data; if the client agrees in writing,
that development could run on rented GPU time meanwhile. Absent that
agreement, development waits for the box.
