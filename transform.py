"""Clean, validate, and summarize parsed EPG data using pandas."""
import pandas as pd

from parse import parse_epg


def build_channels_df(channels):
    return pd.DataFrame(channels)


def build_programmes_df(programmes):
    df = pd.DataFrame(programmes)

    df["start"] = pd.to_datetime(df["start"], utc=True, errors="coerce")
    df["stop"] = pd.to_datetime(df["stop"], utc=True, errors="coerce")

    missing_description = int(df["description"].isna().sum())
    missing_category = int(df["category"].isna().sum())

    df["description"] = df["description"].fillna("")
    df["category"] = df["category"].fillna("Uncategorized")

    before_validation = len(df)
    df = df[df["start"] <= df["stop"]]
    dropped_invalid_range = before_validation - len(df)

    before_dedup = len(df)
    df = df.drop_duplicates(subset=["channel_id", "start"], keep="first")
    dropped_duplicates = before_dedup - len(df)

    df["ingested_at"] = pd.Timestamp.now(tz="UTC")

    stats = {
        "missing_description": missing_description,
        "missing_category": missing_category,
        "dropped_invalid_range": dropped_invalid_range,
        "dropped_duplicates": dropped_duplicates,
    }
    return df, stats


def print_summary(channels_df, programmes_df, stats):
    print("\n--- Summary ---")
    print(f"Total channels: {len(channels_df)}")
    print(f"Total programmes (after cleaning): {len(programmes_df)}")
    print(f"Missing descriptions (filled with ''): {stats['missing_description']}")
    print(f"Missing categories (filled with 'Uncategorized'): {stats['missing_category']}")
    print(f"Dropped rows (start after stop / unparseable time): {stats['dropped_invalid_range']}")
    print(f"Dropped duplicate programmes (same channel + start): {stats['dropped_duplicates']}")


def transform(channels, programmes):
    channels_df = build_channels_df(channels)
    programmes_df, stats = build_programmes_df(programmes)
    print_summary(channels_df, programmes_df, stats)
    return channels_df, programmes_df


if __name__ == "__main__":
    channels, programmes = parse_epg()
    transform(channels, programmes)