import os

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREDICTIONS = os.path.join(BASE_DIR, "data", "predicted_ic_full.parquet")
POSITIVES = os.path.join(BASE_DIR, "data", "positive_generic.parquet")
NODES_TABLE = os.path.join(BASE_DIR, "data", "nodes_table.parquet")

PERCENTILES = (1, 5, 10, 25, 50, 75, 90)
FLAG_SHARES = (0.5, 1.0, 2.0, 5.0, 10.0)
N_EXAMPLES = 15
NAME_WIDTH = 46


def load() -> tuple[int, pd.DataFrame, np.ndarray]:
    predictions = pd.read_parquet(PREDICTIONS).rename(
        columns={"predicted_ic": "predicted"})
    positives = pd.read_parquet(POSITIVES, columns=["id", "name"])
    curated = pd.read_parquet(NODES_TABLE,
                              columns=["id", "information_content"])

    generics = positives.merge(predictions, on="id").merge(curated, on="id")
    return len(positives), generics, predictions["predicted"].to_numpy()


def report_coverage(n_total: int, generics: pd.DataFrame) -> None:
    """
    Print how many labelled generics could be scored at all.

    Input:
        n_total: labelled generics before the join.
        generics: the subset carrying a prediction.

    Output:
        None. Writes to stdout. Anything short of full coverage means the
        join lost nodes, not that the model declined to score them: every
        node in the graph gets a prediction whether or not it has an IC.
    """
    scored = len(generics)
    curated = int(generics["information_content"].notna().sum())
    print(f"\nlabelled generics:      {n_total:>9,}")
    print(f"  scored:               {scored:>9,}"
          f"   {scored / n_total:>6.1%}")
    print(f"  of those, curated IC: {curated:>9,}"
          f"   {curated / scored:>6.1%}")


def report_distribution(generics: pd.DataFrame,
                        population: np.ndarray) -> None:
    """
    Print the predicted IC distribution for generics against the graph.

    Input:
        generics: scored generics with a predicted column.
        population: predicted IC over every labelled node.

    Output:
        None. Writes to stdout. The final line places the generic median on
        the population's percentile scale, which is the single number that
        says whether the feature separates: a median at the 1st percentile
        means the model puts almost the whole graph above them.

        The two generic rows split on whether a curated IC exists. Those
        that have one were in the training set, so if they score lower than
        the rest the recall figures below are optimistic.
    """
    predicted = generics["predicted"].to_numpy()
    curated = generics["information_content"].notna()
    labels = "".join(f"{'p' + str(p):>8}" for p in PERCENTILES)
    header = f"{'predicted IC':<20}{'n':>9}{labels}"
    print(f"\n{header}\n{'-' * len(header)}")

    rows = (("generic, curated IC", predicted[curated.to_numpy()]),
            ("generic, no IC", predicted[~curated.to_numpy()]),
            ("generic, all", predicted),
            ("population", population))
    for label, values in rows:
        cells = "".join(f"{v:>8.1f}"
                        for v in np.percentile(values, PERCENTILES))
        print(f"{label:<20}{len(values):>9,}{cells}")

    rank = (population < np.median(predicted)).mean()
    print(f"\n{rank:.2%} of the population is predicted below the generic "
          "median")


def report_calibration(generics: pd.DataFrame) -> None:
    """
    Print curated against predicted IC for the scored generics.

    Input:
        generics: scored generics with information_content and predicted.

    Output:
        None. Writes to stdout, over the generics that have a curated IC to
        compare against. A predicted mean well above the curated one is
        expected rather than alarming: the features explain part of the IC
        variance, and squared error will not send a prediction further from
        the mean than the evidence supports.
    """
    scored = generics.dropna(subset=["information_content"])
    header = (f"{'IC where curated (n=' + str(len(scored)) + ')':<30}"
              f"{'mean':>9}{'median':>9}{'min':>9}{'max':>9}")
    print(f"\n{header}\n{'-' * len(header)}")

    for label, column in (("curated", "information_content"),
                          ("predicted", "predicted")):
        values = scored[column].to_numpy()
        print(f"{label:<30}{values.mean():>9.1f}{np.median(values):>9.1f}"
              f"{values.min():>9.1f}{values.max():>9.1f}")


def report_recall(generics: pd.DataFrame, population: np.ndarray) -> None:
    """
    Print how many generics a threshold catches for what it costs.

    Input:
        generics: scored generics with a predicted column.
        population: predicted IC over every labelled node.

    Output:
        None. Writes to stdout. Each row is a candidate split point stated
        as the share of the graph it flags. `lift` is recall divided by
        that share: 1x is a coin flip, and anything well above it means the
        feature carries information the classifier can act on.
    """
    predicted = generics["predicted"].to_numpy()
    header = (f"{'flag this share':<20}{'cutoff':>9}{'caught':>9}"
              f"{'recall':>9}{'lift':>9}")
    print(f"\n{header}\n{'-' * len(header)}")

    for share in FLAG_SHARES:
        cutoff = np.percentile(population, share)
        caught = int((predicted < cutoff).sum())
        recall = caught / len(predicted)
        print(f"{f'{share}% of graph':<20}{cutoff:>9.1f}{caught:>9,}"
              f"{recall:>9.1%}{recall / (share / 100):>8.1f}x")


def report_misses(generics: pd.DataFrame) -> None:
    """
    Print the generics the model placed highest.

    Input:
        generics: scored generics with name, information_content and
            predicted.

    Output:
        None. Writes to stdout. These are the concepts a threshold would
        miss, listed by name so they can be judged individually rather than
        through an aggregate.
    """
    header = (f"{'worst misses':<{NAME_WIDTH}}{'curated':>9}"
              f"{'predicted':>11}")
    print(f"\n{header}\n{'-' * len(header)}")

    worst = generics.nlargest(N_EXAMPLES, "predicted")
    for row in worst.itertuples():
        name = (row.name or row.id)[:NAME_WIDTH - 2]
        print(f"{name:<{NAME_WIDTH}}{row.information_content:>9.1f}"
              f"{row.predicted:>11.1f}")


def main() -> None:
    n_total, generics, population = load()
    report_coverage(n_total, generics)
    report_distribution(generics, population)
    report_calibration(generics)
    report_recall(generics, population)
    report_misses(generics)


if __name__ == "__main__":
    main()
