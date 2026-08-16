"""P6c — LP-MPPI (저역통과 colored noise) vs 백색 MPPI (arXiv:2503.11717 아이디어).
노트 공간에서 인접-노트 상관 노이즈(1차 IIR, alpha)로 샘플링 → 부드러운 τ 섭동.
동일 예산 2400, lambda 0.05."""
import json
import numpy as np
from pathlib import Path
import g22_p6_sampling as P6

OUT = Path(__file__).parent / "p6c_lpmppi.json"


def run_lpmppi(pool, x0, budget, lam=0.05, sigma=2.0, pop=60, alpha=0.6, seed=7):
    x = x0.copy(); nev = 0
    rng = np.random.default_rng(seed)
    n = len(x)
    for it in range(budget // pop):
        w_ = rng.normal(0, sigma, (pop, n))
        eps = np.empty_like(w_)
        for j in (0, P6.NK):                       # 관절별로 저역 필터
            seg = w_[:, j:j + P6.NK]
            f = np.empty_like(seg)
            f[:, 0] = seg[:, 0]
            for k in range(1, P6.NK):
                f[:, k] = alpha * f[:, k - 1] + (1 - alpha) * seg[:, k]
            eps[:, j:j + P6.NK] = f / np.sqrt((1 - alpha) / (1 + alpha) + 1e-9)  # 분산 보정(근사)
        eps[0] = 0.0
        rs = pool.map(P6.rollout, [(x + e, 0.0, False, 0) for e in eps])
        cc = np.array([r[0] for r in rs]); nev += pop
        w = np.exp(-(cc - cc.min()) / lam); w /= w.sum()
        x = x + (w[:, None] * eps).sum(0)
        sigma = max(0.4, sigma * 0.97)
    c, h, pen = P6.rollout((x, 0.0, False, 0))
    return float(h), float(pen), nev


def main():
    import multiprocessing as mp
    P6.winit()
    pool = mp.Pool(10, initializer=P6.winit)
    x0 = P6.x_from_csv()
    res = {}
    for alpha in [0.0, 0.5, 0.8]:
        h, pen, nev = run_lpmppi(pool, x0, 2400, alpha=alpha)
        res[str(alpha)] = dict(h=h, pen=pen)
        print(f"LP-MPPI alpha={alpha}: h={h:.4f} pen={pen:.4f}", flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("saved", OUT.name, flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
