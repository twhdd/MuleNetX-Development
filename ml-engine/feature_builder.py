import os
import pandas as pd
from typing import Optional

from graph_engine.point_in_time_features import build_point_in_time_dataset, CANONICAL_FEATURES_PATH

OUTPUT_PATH = CANONICAL_FEATURES_PATH


def build_feature_dataset(output_path: Optional[str] = None) -> pd.DataFrame:
    """
    Builds the point-in-time, leak-free feature dataset for accounts across
    training, validation, and testing time windows.
    """
    if output_path is None:
        output_path = OUTPUT_PATH

    df = build_point_in_time_dataset(output_path=output_path)
    return df


if __name__ == "__main__":
    df = build_feature_dataset()
    print("Feature dataset preview:")
    print(df.head())
    print("\nLabel distribution:")
    print(df["label"].value_counts())
