"""metrics.py — Statistical metrics for benchmark evaluation."""
import math


def stats(errors):
    """MAE, RMSE, bias from a list of errors (None values skipped)."""
    errs = [e for e in errors if e is not None and not math.isnan(e)]
    if not errs:
        return dict(n=0, mae=float("nan"), rmse=float("nan"), bias=float("nan"))
    n = len(errs)
    return dict(n=n,
                mae =sum(abs(e) for e in errs) / n,
                rmse=math.sqrt(sum(e**2 for e in errs) / n),
                bias=sum(errs) / n)


def spearman(xs, ys):
    """Spearman rank correlation for paired lists (None pairs skipped)."""
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None
             and not math.isnan(x) and not math.isnan(y)]
    if len(pairs) < 2:
        return float("nan")
    xs_, ys_ = zip(*pairs)
    rx = _ranks(xs_)
    ry = _ranks(ys_)
    return pearson(rx, ry)


def pearson(xs, ys):
    """Pearson r correlation for paired lists."""
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None
             and not math.isnan(x) and not math.isnan(y)]
    if len(pairs) < 2:
        return float("nan")
    n = len(pairs)
    xs_, ys_ = zip(*pairs)
    mx = sum(xs_) / n
    my = sum(ys_) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs_, ys_))
    dx  = math.sqrt(sum((x - mx)**2 for x in xs_))
    dy  = math.sqrt(sum((y - my)**2 for y in ys_))
    if dx < 1e-12 or dy < 1e-12:
        return float("nan")
    return num / (dx * dy)


def _ranks(xs):
    """Average ranks for tied values."""
    sorted_idx = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j < len(xs) - 1 and xs[sorted_idx[j+1]] == xs[sorted_idx[j]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[sorted_idx[k]] = avg
        i = j + 1
    return ranks
