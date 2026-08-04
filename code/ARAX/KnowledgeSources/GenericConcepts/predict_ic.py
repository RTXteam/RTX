"""
Predict information content from name and description embeddings.

Fits ridge from the embedded text plus a category one-hot to curated IC, and
returns an out-of-fold prediction for every labelled node.

Input:
    NODES_TABLE: parquet with most_specific_category and information_content.
    NODE_EMBEDDINGS: float32 embeddings, one row per node, same row order.

Output:
    Per-category, per-IC-band and per-text-source results to stdout.
    PREDICTIONS: out-of-fold predicted IC for every labelled node.
"""

import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODES_TABLE = os.path.join(BASE_DIR, "data", "nodes_table.parquet")
NODE_EMBEDDINGS = os.path.expanduser(
    "~/Desktop/code/large_files/node_embeddings.npy")
PREDICTIONS = os.path.join(BASE_DIR, "data", "predicted_ic.parquet")
PREDICTED_ALL = os.path.join(BASE_DIR, "data", "predicted_ic_full.parquet")

ALPHAS = (0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
IC_BANDS = (0.0, 50.0, 66.0, 88.0, 95.0, 100.0)
N_FOLDS = 5
CHUNK_SIZE = 50_000
MIN_GROUP_SIZE = 500
RANDOM_SEED = 2654


def fold_moments(features: np.ndarray, targets: np.ndarray,
                 folds: np.ndarray) -> tuple[np.ndarray, ...]:
    """
    Accumulate per-fold Gram matrices, cross products and sums in one pass.

    Gram matrices are additive over disjoint row sets, so the system for any
    union of folds is the sum of theirs. That makes every training
    combination available from one pass instead of one pass per fold.

    Input:
        features: float32 design matrix.
        targets: IC values.
        folds: fold index per row.

    Output:
        gram, cross, feature_sum, target_sum and count, indexed by fold.
        Accumulation is float64 over float32 blocks, so the normal equations
        stay well conditioned without a float64 copy of the whole matrix.
    """
    dim = features.shape[1]
    gram = np.zeros((N_FOLDS, dim, dim))
    cross = np.zeros((N_FOLDS, dim))
    feature_sum = np.zeros((N_FOLDS, dim))
    target_sum = np.zeros(N_FOLDS)
    count = np.zeros(N_FOLDS)

    for start in range(0, len(features), CHUNK_SIZE):
        stop = start + CHUNK_SIZE
        block = features[start:stop].astype(np.float64)
        block_targets = targets[start:stop]
        block_folds = folds[start:stop]
        for fold in range(N_FOLDS):
            member = block_folds == fold
            if not member.any():
                continue
            rows, values = block[member], block_targets[member]
            gram[fold] += rows.T @ rows
            cross[fold] += rows.T @ values
            feature_sum[fold] += rows.sum(axis=0)
            target_sum[fold] += values.sum()
            count[fold] += len(rows)

    return gram, cross, feature_sum, target_sum, count


def solve(moments: tuple[np.ndarray, ...], keep: list[int],
          alphas: tuple[float, ...]) -> tuple[list[np.ndarray],
                                              np.ndarray, float]:
    """
    Fit centred ridge on the union of the kept folds, once per penalty.

    Centring supplies an unpenalised intercept, so the penalty shrinks slopes
    rather than the overall IC level. One eigendecomposition serves every
    penalty, because alpha only shifts the eigenvalues.

    Input:
        moments: output of fold_moments.
        keep: fold indices to train on.
        alphas: penalties to solve for.

    Output:
        Weights per penalty, plus the feature means and target mean needed to
        apply them.
    """
    gram, cross, feature_sum, target_sum, count = moments
    total = count[keep].sum()
    feature_mean = feature_sum[keep].sum(axis=0) / total
    target_mean = target_sum[keep].sum() / total
    gram_c = (gram[keep].sum(axis=0)
              - total * np.outer(feature_mean, feature_mean))
    cross_c = (cross[keep].sum(axis=0)
               - total * feature_mean * target_mean)

    values, vectors = np.linalg.eigh(gram_c)
    projected = vectors.T @ cross_c
    weights = [vectors @ (projected / (values + a)) for a in alphas]
    return weights, feature_mean, target_mean


def out_of_fold(features: np.ndarray, targets: np.ndarray,
                folds: np.ndarray,
                moments: tuple[np.ndarray, ...]
                ) -> tuple[np.ndarray, list[float]]:
    """
    Predict every row with a model that never saw it.

    An inner fold selects the penalty, so it is never chosen using data the
    held-out fold should be blind to. Selection uses squared error, the loss
    ridge minimises; rank correlation is reported afterwards, but optimising
    it directly picks erratic penalties.

    Input:
        features: design matrix.
        targets: IC values.
        folds: fold index per row.
        moments: output of fold_moments over the same rows.

    Output:
        Predictions aligned to features, and the penalty chosen per fold.
    """
    predictions = np.empty(len(features))
    chosen = []

    for fold in range(N_FOLDS):
        inner = (fold + 1) % N_FOLDS
        keep = [k for k in range(N_FOLDS) if k not in (fold, inner)]
        weights, feature_mean, target_mean = solve(moments, keep, ALPHAS)

        rows = folds == inner
        block = features[rows] - feature_mean
        errors = [np.mean((block @ w + target_mean - targets[rows]) ** 2)
                  for w in weights]
        alpha = ALPHAS[int(np.argmin(errors))]
        chosen.append(alpha)

        keep = [k for k in range(N_FOLDS) if k != fold]
        weights, feature_mean, target_mean = solve(moments, keep, (alpha,))
        rows = folds == fold
        predictions[rows] = ((features[rows] - feature_mean) @ weights[0]
                             + target_mean)

    return predictions, chosen


def score_all(embeddings: np.ndarray, dummies: np.ndarray,
              moments: tuple[np.ndarray, ...], alpha: float) -> np.ndarray:
    """
    Fit on every labelled row and predict IC for the whole graph.

    Input:
        embeddings: memmapped embeddings, one row per node.
        dummies: category one-hot, one row per node.
        moments: output of fold_moments over the labelled rows.
        alpha: penalty to fit with.

    Output:
        Predicted IC for every node. The design matrix is rebuilt one chunk
        at a time because the full graph is roughly three times the size of
        the labelled subset and never needs to exist at once.
    """
    weights, feature_mean, target_mean = solve(
        moments, list(range(N_FOLDS)), (alpha,))

    predictions = np.empty(len(dummies))
    for start in range(0, len(dummies), CHUNK_SIZE):
        stop = start + CHUNK_SIZE
        block = np.hstack([embeddings[start:stop], dummies[start:stop]])
        predictions[start:stop] = ((block - feature_mean) @ weights[0]
                                   + target_mean)
    return predictions


def summarise(label: str, predicted: np.ndarray,
              truth: np.ndarray) -> str:
    """
    Format one result row.

    Input:
        label: row label.
        predicted: predicted IC.
        truth: curated IC.

    Output:
        A formatted line. `spread` is the ratio of predicted to actual
        standard deviation: ridge pulls predictions toward the mean, so a
        low value means the model is hedging rather than committing, which a
        rank correlation on its own will not reveal.
    """
    return (f"{label:<40}{len(truth):>9,}"
            f"{spearmanr(predicted, truth).statistic:>8.3f}"
            f"{np.abs(predicted - truth).mean():>8.2f}"
            f"{predicted.std() / truth.std():>8.2f}"
            f"{truth.mean():>8.1f}{predicted.mean():>8.1f}")


def summarise_band(label: str, predicted: np.ndarray, truth: np.ndarray,
                   total_error: float) -> str:
    """
    Format one IC-band row.

    Input:
        label: band label.
        predicted: predicted IC.
        truth: curated IC.
        total_error: squared error summed over every labelled node.

    Output:
        A formatted line. Rank correlation is omitted because a band is a
        restricted range of the target, where it is close to meaningless.
        `share` is the band's fraction of total squared error: squared loss
        weights by the size of the miss rather than by row count, so a band
        holding a small share of the rows can still dominate the fit.
    """
    error = ((predicted - truth) ** 2).sum()
    return (f"{label:<40}{len(truth):>9,}"
            f"{truth.mean():>8.1f}{predicted.mean():>8.1f}"
            f"{np.abs(predicted - truth).mean():>8.2f}"
            f"{error / total_error:>11.1%}")


def report_categories(table: pd.DataFrame) -> None:
    """
    Print per-category results, largest category first.

    Input:
        table: labelled rows with most_specific_category,
            information_content and predicted.

    Output:
        None. Writes to stdout. Results are per category rather than pooled
        because a pooled figure credits the model for separating chemicals
        from diseases, which says nothing about ranking within either. The
        pooled row is printed last for contrast, not as the headline.
    """
    header = (f"{'category':<40}{'n':>9}{'rho':>8}{'MAE':>8}"
              f"{'spread':>8}{'true':>8}{'pred':>8}")
    print(f"\n{header}\n{'-' * len(header)}")

    groups = sorted(table.groupby("most_specific_category", observed=True),
                    key=lambda item: -len(item[1]))
    for category, group in groups:
        if len(group) < MIN_GROUP_SIZE:
            continue
        print(summarise(category.replace("biolink:", ""),
                        group["predicted"].to_numpy(),
                        group["information_content"].to_numpy()))

    print("-" * len(header))
    print(summarise("pooled", table["predicted"].to_numpy(),
                    table["information_content"].to_numpy()))


def report_bands(table: pd.DataFrame) -> None:
    """
    Print results grouped by true IC, lowest band first.

    Input:
        table: labelled rows with information_content and predicted.

    Output:
        None. Writes to stdout. Curated IC piles up against 100, so the
        per-category table is dominated by nodes the model already places
        correctly. Banding by the true value exposes the sparse low-IC tail
        where generic concepts actually live, which is the region the
        feature has to be useful in.
    """
    truth = table["information_content"].to_numpy()
    total_error = ((table["predicted"].to_numpy() - truth) ** 2).sum()

    header = (f"{'true IC band':<40}{'n':>9}{'true':>8}{'pred':>8}"
              f"{'MAE':>8}{'err share':>11}")
    print(f"\n{header}\n{'-' * len(header)}")

    bands = pd.cut(table["information_content"], bins=IC_BANDS,
                   include_lowest=True)
    for band, group in table.groupby(bands, observed=True):
        print(summarise_band(f"{band.left:g} - {band.right:g}",
                             group["predicted"].to_numpy(),
                             group["information_content"].to_numpy(),
                             total_error))


def report_text_source(table: pd.DataFrame) -> None:
    """
    Print results split on whether the embedded text had a description.

    Input:
        table: labelled rows with has_description, information_content and
            predicted.

    Output:
        None. Writes to stdout. Only 34.5% of nodes carry a description, so
        the rest were embedded from a bare name. A gap between the two rows
        means the description is carrying signal and a model trained on
        definitions would extract more of it; no gap means SapBERT is
        ignoring the description entirely, which argues for switching just
        as strongly.
    """
    header = (f"{'text source':<40}{'n':>9}{'rho':>8}{'MAE':>8}"
              f"{'spread':>8}{'true':>8}{'pred':>8}")
    print(f"\n{header}\n{'-' * len(header)}")

    has_text = table["has_description"]
    for label, mask in (("name: description", has_text),
                        ("name only", ~has_text)):
        group = table[mask]
        print(summarise(label, group["predicted"].to_numpy(),
                        group["information_content"].to_numpy()))


def report(table: pd.DataFrame, chosen: list[float]) -> None:
    """
    Print every result section.

    Input:
        table: labelled rows with most_specific_category, has_description,
            information_content and predicted.
        chosen: penalty selected in each fold.

    Output:
        None. Writes to stdout.
    """
    print("\nalpha per fold: " + ", ".join(f"{a:g}" for a in chosen))
    if len(set(chosen)) == 1 and chosen[0] in (ALPHAS[0], ALPHAS[-1]):
        print(f"  warning: every fold chose {chosen[0]:g}, an edge of the "
              "grid; widen ALPHAS")

    report_categories(table)
    report_bands(table)
    report_text_source(table)


def main() -> None:
    nodes = pd.read_parquet(
        NODES_TABLE,
        columns=["id", "most_specific_category", "information_content",
                 "description"])
    nodes["has_description"] = nodes["description"].notna()
    nodes = nodes.drop(columns=["description"])

    embeddings = np.load(NODE_EMBEDDINGS, mmap_mode="r")
    dummies = pd.get_dummies(
        nodes["most_specific_category"]).to_numpy("float32")

    labelled = np.where(nodes["information_content"].notna())[0]
    features = np.hstack([embeddings[labelled], dummies[labelled]])
    targets = nodes["information_content"].to_numpy()[labelled]
    print(f"labelled nodes: {len(labelled):,}   "
          f"features: {features.shape[1]:,}")

    folds = np.random.default_rng(RANDOM_SEED).integers(
        0, N_FOLDS, size=len(labelled))
    moments = fold_moments(features, targets, folds)
    predictions, chosen = out_of_fold(features, targets, folds, moments)

    table = nodes.iloc[labelled].copy()
    table["predicted"] = predictions
    report(table, chosen)

    table[["id", "predicted"]].to_parquet(PREDICTIONS, index=False)
    print(f"\nwrote {len(table):,} predictions to {PREDICTIONS}")
    alpha = max(set(chosen), key=chosen.count)
    scored = score_all(embeddings, dummies, moments, alpha)
    scored[labelled] = predictions

    pd.DataFrame({"id": nodes["id"], "predicted_ic": scored}).to_parquet(
        PREDICTED_ALL, index=False)
    print(f"scored the full graph at alpha {alpha:g}: {len(scored):,} "
          f"nodes to {PREDICTED_ALL}")


if __name__ == "__main__":
    main()
