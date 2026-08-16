"""Phase 4 frontier plot: (left) sit2stand vs jump Pareto, (right) jump-weight vs h_ratio."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P4 = Path(__file__).resolve().parent
fr = json.load(open(P4 / "phase4_frontier.json"))

lams = [f["lam"] for f in fr]
s2s = [f["s2s"] for f in fr]
jump = [f["jump"] for f in fr]
hr = [f["h_ratio"] for f in fr]

fig, ax = plt.subplots(1, 2, figsize=(13, 5))
# Left: Pareto sit2stand vs jump
ax[0].plot(s2s, jump, "-o")
for i, f in enumerate(fr):
    ax[0].annotate(f"λ={f['lam']}", (s2s[i], jump[i]), fontsize=8,
                   textcoords="offset points", xytext=(6, 4))
ax[0].set_xlabel("sit2stand score (7 subs)")
ax[0].set_ylabel("jump score (24 subs)")
ax[0].set_title("Pareto: jump weight trades sit2stand vs jump")
ax[0].grid(alpha=0.3)

# Right: jump-weight vs h_ratio
xs = list(range(len(fr)))
ax[1].plot(xs, hr, "-s")
ax[1].axhline(1.0, ls="--", label="real (h_ratio=1.0)")
ax[1].set_xticks(xs); ax[1].set_xticklabels([str(l) for l in lams], rotation=30, fontsize=8)
ax[1].set_xlabel("jump weight λ")
ax[1].set_ylabel("jump h_sim / h_real")
ax[1].set_ylim(0, 1.05)
ax[1].set_title("Even max jump-favoring caps at ~0.62\n(fundamental Mode-A energy deficit)")
ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)

fig.tight_layout()
out = P4 / "frontier.png"
fig.savefig(out, dpi=120)
print("Written:", out)
