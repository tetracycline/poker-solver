"""Deterministic, bounded batches of full flop-to-river DCFR solves.

A job is a SINGLE full three-street game, not a stitched turn/river re-solve.
Only output extraction is sampled; the underlying solve includes all legal runouts.
Full six-size trees can be too large; MEMORY_BUDGET_EXCEEDED is a valid,
explicit failure, never silently replaced by a smaller tree.
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
POST = HERE.parent
sys.path.insert(0, str(HERE))
from flops import sample

SIZES = {
    "smoke": "33%",
    "medium": "33%,75%",
    "full": "33%,50%,75%,100%,150%,a",
}
SPOTS = ("BTN_BB", "CO_BB", "SB_BB", "UTG_BB", "HJ_BB", "SB3_BTN", "BB3_BTN")
DECK = tuple(r + s for r in "23456789TJQKA" for s in "cdhs")


def sampled_runouts(flop, turns, rivers):
    """Stable sample without global RNG or dependence on Python hash randomization."""
    cards = (flop[:2], flop[2:4], flop[4:6])
    remain = [c for c in DECK if c not in cards]
    rank = lambda key, card: hashlib.sha256((key + ":" + card).encode()).digest()
    turn_cards = sorted(remain, key=lambda c: rank("turn:" + flop, c))[:turns]
    for turn in turn_cards:
        river_cards = sorted((c for c in remain if c != turn),
                             key=lambda c: rank("river:" + flop + turn, c))[:rivers]
        yield turn, river_cards


def extraction(flop, turns, rivers):
    """Extract flop, sampled turn and sampled river check/check paths.

    The extraction does not change the solved tree. Other paths remain in
    the full-game equilibrium, although they are not exported by this batch.
    """
    ex = [{"prefix": [], "street": True}]
    for turn, rs in sampled_runouts(flop, turns, rivers):
        ex.append({"prefix": ["x", "x", turn], "street": True})
        for river in rs:
            ex.append({"prefix": ["x", "x", turn, "x", "x", river],
                       "street": True})
    return ex


def build_job(spot, flop, args, out):
    from job import make_job
    job = make_job(spot, "gto", flop, str(out), iters=args.iters,
                   target=args.target_pct, compress=True,
                   extract=extraction(flop, args.turns, args.rivers))
    sizes = SIZES[args.preset]
    for street in ("flop", "turn", "river"):
        job[street + "_ip"] = sizes
        job[street + "_oop"] = sizes
        job[street + "_raise"] = args.raises
    # Keep donks empty as in existing driver, to control memory.
    job["turn_donk"] = ""
    job["river_donk"] = ""
    job["max_memory_gb"] = args.max_memory_gb
    return job


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spot", choices=SPOTS, required=True)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--flop-total", type=int, default=90)
    p.add_argument("--preset", choices=tuple(SIZES), default="smoke")
    p.add_argument("--raises", default="3x,a")
    p.add_argument("--turns", type=int, default=1)
    p.add_argument("--rivers", type=int, default=1)
    p.add_argument("--iters", type=int, default=300)
    p.add_argument("--target-pct", type=float, default=0.5)
    p.add_argument("--max-memory-gb", type=float, default=8)
    p.add_argument("--output", type=pathlib.Path, default=POST / "batch_out")
    args = p.parse_args(argv)
    if min(args.count, args.flop_total, args.turns, args.rivers, args.iters) <= 0 or args.start < 0:
        p.error("positive counts/iterations and nonnegative start required")
    if not 0 < args.max_memory_gb <= 128 or not 0 < args.target_pct < 100:
        p.error("invalid memory or convergence target")
    if args.start + args.count > args.flop_total:
        p.error("batch extends beyond flop-total")
    if not args.raises or any(v.strip() == "" for v in args.raises.split(",")):
        p.error("invalid raises")
    from job import DRV
    if not pathlib.Path(DRV).exists():
        p.error("Rust driver missing; build pfdriver first")
    args.output.mkdir(parents=True, exist_ok=True)
    flops = sample(args.flop_total)
    failed = 0
    manifest = []
    for index in range(args.start, args.start + args.count):
        flop = flops[index]
        stem = f"{args.spot}_{index:04d}_{flop}_{args.preset}"
        out = args.output / (stem + ".json")
        job_path = args.output / (stem + ".job.json")
        job = build_job(args.spot, flop, args, out)
        job_path.write_text(json.dumps(job, indent=2), encoding="utf8")
        status = "OK"
        if not out.exists():
            with (args.output / (stem + ".log")).open("w", encoding="utf8") as log:
                result = subprocess.run([DRV, str(job_path)], stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                status = "MEMORY_BUDGET_EXCEEDED" if result.returncode == 42 else "SOLVER_FAILED"
        if status == "OK":
            if not out.exists():
                status = "OUTPUT_MISSING"
            else:
                try:
                    data = json.loads(out.read_text(encoding="utf8"))
                    if not data["info"].get("gto_converged", False):
                        status = "NOT_CONVERGED"
                except (KeyError, ValueError, OSError):
                    status = "INVALID_OUTPUT"
        failed += status != "OK"
        manifest.append(dict(index=index, flop=flop, status=status,
                             output=out.name if out.exists() else None,
                             job=job_path.name))
        print(f"{stem}: {status}", flush=True)
    (args.output / f"manifest_{args.spot}_{args.start:04d}.json").write_text(
        json.dumps({"settings": vars(args) | {"output": str(args.output)},
                    "runs": manifest}, indent=2), encoding="utf8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
