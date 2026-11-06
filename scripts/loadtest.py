"""Teste de carga do dashboard Streamlit: N sessões simultâneas via websocket.

Uso (com o dashboard no ar e o PID do processo Streamlit):
    .venv/bin/python scripts/loadtest.py --base http://127.0.0.1:8501 \
        --users 200 --ramp 0 --pid <PID> --out /tmp/carga.json

Cada usuário virtual:
  1. GET /            (HTML estático)
  2. abre ws /_stcore/stream (subprotocolo "streamlit")
  3. envia rerun_script (equivale a abrir a página) e mede:
       - ttfd: tempo até o primeiro delta (primeiro conteúdo)
       - full: tempo até script_finished (página completa)
  4. envia um segundo rerun_script (interação, cenário D2) e mede o tempo.
"""

import argparse
import asyncio
import json
import statistics
import time
import urllib.request

import websockets
from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg

TIMEOUT_S = 120


def rerun_msg() -> bytes:
    msg = BackMsg()
    msg.rerun_script.query_string = ""
    msg.rerun_script.page_script_hash = ""
    return msg.SerializeToString()


async def run_script(ws) -> tuple[float | None, float, int]:
    t0 = time.perf_counter()
    await ws.send(rerun_msg())
    first_delta = None
    deltas = 0
    while True:
        raw = await asyncio.wait_for(ws.recv(), TIMEOUT_S)
        fm = ForwardMsg()
        fm.ParseFromString(raw)
        kind = fm.WhichOneof("type")
        if kind == "delta":
            deltas += 1
            if first_delta is None:
                first_delta = time.perf_counter() - t0
        elif kind == "script_finished":
            if fm.script_finished in (ForwardMsg.FINISHED_SUCCESSFULLY,):
                return first_delta, time.perf_counter() - t0, deltas
            if fm.script_finished == ForwardMsg.FINISHED_EARLY_FOR_RERUN:
                continue
            raise RuntimeError(f"script_finished={fm.script_finished}")


async def user(base: str, start_at: float, out: list):
    await asyncio.sleep(max(0.0, start_at - time.perf_counter()))
    r = {"ok": False}
    t0 = time.perf_counter()
    try:
        await asyncio.to_thread(
            lambda: urllib.request.urlopen(base + "/", timeout=30).read())
        r["http"] = time.perf_counter() - t0
        ws_url = base.replace("http", "ws") + "/_stcore/stream"
        async with websockets.connect(
            ws_url, subprotocols=["streamlit"], max_size=None,
            open_timeout=30, ping_interval=None,
        ) as ws:
            r["connect"] = time.perf_counter() - t0
            ttfd, full, deltas = await run_script(ws)
            r["ttfd"] = (r["connect"] + ttfd) if ttfd is not None else None
            r["full"] = r["connect"] + full
            r["deltas"] = deltas
            _, rerun, _ = await run_script(ws)
            r["rerun"] = rerun
            r["ok"] = True
    except Exception as exc:  # noqa: BLE001
        r["error"] = f"{type(exc).__name__}: {exc}"[:200]
    out.append(r)


def pct(values, p):
    if not values:
        return None
    s = sorted(values)
    k = max(0, min(len(s) - 1, round(p / 100 * len(s) + 0.5) - 1))
    return s[k]


async def sample_proc(pid: int, stop: asyncio.Event, samples: list):
    ticks = 100
    def read():
        with open(f"/proc/{pid}/stat") as f:
            parts = f.read().split(")")[1].split()
        cpu = (int(parts[11]) + int(parts[12])) / ticks
        with open(f"/proc/{pid}/status") as f:
            rss = next(int(l.split()[1]) for l in f if l.startswith("VmRSS"))
        return cpu, rss / 1024
    last_cpu, _ = read()
    last_t = time.perf_counter()
    while not stop.is_set():
        await asyncio.sleep(0.5)
        cpu, rss = read()
        now = time.perf_counter()
        samples.append({"t": now, "cpu_pct": 100 * (cpu - last_cpu) / (now - last_t),
                        "rss_mb": rss})
        last_cpu, last_t = cpu, now


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8501")
    ap.add_argument("--users", type=int, default=200)
    ap.add_argument("--ramp", type=float, default=0.0, help="s para iniciar todos")
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    stop, samples, results = asyncio.Event(), [], []
    sampler = asyncio.create_task(sample_proc(a.pid, stop, samples))
    await asyncio.sleep(1.5)
    t_start = time.perf_counter() + 0.5
    tasks = [user(a.base, t_start + (a.ramp * i / max(1, a.users - 1)), results)
             for i in range(a.users)]
    await asyncio.gather(*tasks)
    wall = time.perf_counter() - t_start
    await asyncio.sleep(1.0)
    stop.set()
    await sampler

    ok = [r for r in results if r["ok"]]
    def stats(key):
        v = [r[key] for r in ok if r.get(key) is not None]
        return {"p50": pct(v, 50), "p95": pct(v, 95), "p99": pct(v, 99),
                "max": max(v) if v else None,
                "mean": statistics.mean(v) if v else None}
    errors = {}
    for r in results:
        if not r["ok"]:
            errors[r["error"]] = errors.get(r["error"], 0) + 1
    busy = [s for s in samples if s["t"] >= t_start]
    summary = {
        "users": a.users, "ramp_s": a.ramp, "wall_s": wall,
        "ok": len(ok), "failed": len(results) - len(ok),
        "fail_pct": 100 * (len(results) - len(ok)) / len(results),
        "http": stats("http"), "connect": stats("connect"),
        "ttfd": stats("ttfd"), "full": stats("full"), "rerun": stats("rerun"),
        "deltas_per_page": stats("deltas")["p50"],
        "rss_mb_before": samples[0]["rss_mb"] if samples else None,
        "rss_mb_peak": max(s["rss_mb"] for s in samples) if samples else None,
        "rss_mb_after": samples[-1]["rss_mb"] if samples else None,
        "cpu_pct_mean": statistics.mean(s["cpu_pct"] for s in busy) if busy else None,
        "cpu_pct_peak": max(s["cpu_pct"] for s in busy) if busy else None,
        "errors": errors,
    }
    with open(a.out, "w") as f:
        json.dump({"summary": summary, "results": results, "samples": samples}, f)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
