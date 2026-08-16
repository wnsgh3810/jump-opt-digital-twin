"""P6b — CMA 예산 스케일링(2400→9600) + 시드 3개 일관성 (봉투 내장 rollout)."""
import json, time
import numpy as np
from pathlib import Path
import g22_p6_sampling as P6

OUT = Path(__file__).parent / "p6b_scale.json"


def run_cma_seed(pool, x0, budget, seed):
    import cma
    es = cma.CMAEvolutionStrategy(x0.tolist(), 1.2,
                                  {"maxfevals": budget, "popsize": 24, "seed": seed, "verbose": -9})
    best = (1e9, None)
    while not es.stop():
        sols = es.ask()
        rs = pool.map(P6.rollout, [(np.array(s), 0.0, False, 0) for s in sols])
        cc = [r[0] for r in rs]
        es.tell(sols, cc)
        i = int(np.argmin(cc))
        if cc[i] < best[0]:
            best = (cc[i], np.array(sols[i]))
    c, h, pen = P6.rollout((best[1], 0.0, False, 0))
    return float(h), float(pen)


def main():
    import multiprocessing as mp
    P6.winit()
    pool = mp.Pool(10, initializer=P6.winit)
    x0 = P6.x_from_csv()
    res = {}
    for budget in [2400, 9600]:
        hs = []
        for seed in [5, 15, 25]:
            t0 = time.time()
            h, pen = run_cma_seed(pool, x0, budget, seed)
            hs.append(h)
            print(f"budget={budget} seed={seed}: h={h:.4f} pen={pen:.4f} "
                  f"[{time.time()-t0:.0f}s]", flush=True)
        res[str(budget)] = hs
    json.dump(res, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
