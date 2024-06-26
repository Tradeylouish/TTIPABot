import datetime
from pathlib import Path
import pandas as pd
from typing import NamedTuple, Iterable

def get_csv_filepaths(folderPath: Path) -> list[Path]:
    """Returns a list of filepaths to all the csv files in time order."""
    # ISO naming format means default sort will time-order
    return sorted(list(folderPath.glob('*.csv')))

def get_latest_csvs(csvFilepaths: list[Path], num: int) -> list[Path]:
    """Returns the latest <num> filepaths based on their ISO dated name."""
    return sorted(csvFilepaths)[-num:]

def validate_date(date: str) -> None:
    """Raises an error if <date> is not in ISO format."""
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        raise ValueError("Incorrect date format, should be YYYY-MM-DD")

def select_filepaths_for_dates(filepaths: list[Path], dates: list[str]) -> list[Path]:
    """Returns a list of paths to files with names matching input dates."""
    datePaths=[]
    for date in dates:
        validate_date(date)
        datePath = next((path for path in filepaths if date in str(path)), None)
        if datePath == None: 
            raise ValueError(f"No file exists for {date}")
        datePaths.append(datePath)

    return datePaths

def csv_to_df(csvPath: Path) -> pd.DataFrame:
    """Converts a csv to a dataframe"""
    return pd.read_csv(csvPath, dtype='string').fillna('')

def csvs_to_dfs(datePaths: list[Path]) -> list[pd.DataFrame]:
    """Returns a list of dataframes from a list of filepaths to csvs."""
    #Read the CSV data into dataframes
    return [csv_to_df(datePath) for datePath in datePaths]

def get_diffs(df_date1: pd.DataFrame, df_date2: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    """Return dataframes showing all the differences in data between two input dataframes."""
    # Merge the dataframes so that differences can be compared
    df_diff = pd.merge(df_date1, df_date2, how="outer", indicator="Exist")

    # Query which rows are different
    df_diff = df_diff.query("Exist != 'both'")

    # Separate rows that have changed into a pair of dataframes
    df_left = df_diff.query("Exist == 'left_only'").sort_values(by = 'Name')
    df_right = df_diff.query("Exist == 'right_only'").sort_values(by = 'Name')

    # TODO - name change detect logic?

    return df_left, df_right

def compare_dfs(df_date1: pd.DataFrame, df_date2: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    """Return a dataframe with data of all the new attorneys, and another with those who changed firms."""
    # Data comparison steps
    df_left, df_right = get_diffs(df_date1, df_date2)
    
    # Find which names are new
    df_names = pd.merge(df_left, df_right, on='Name', how="outer", indicator="NameExist")

    df_newAttorneys = df_names.query("NameExist == 'right_only'")
    df_lapsedAttorneys = df_names.query("NameExist == 'left_only'")
    df_changedDetails = df_names.query("NameExist == 'both'")

    df_changedFirms = df_changedDetails.query("Firm_x != Firm_y")

    # TODO: Consider doing a comparison of registrations and capturing those going from single to dual registered

    # Prep the needed data, replace missing values with empty strings to assist comparisons later on
    df_newAttorneys = df_newAttorneys[['Name', 'Firm_y', 'Registered as_y']].fillna('')
    df_changedFirms = df_changedFirms[['Name', 'Firm_x', 'Firm_y']].fillna('')

    # Reformat for readability
    df_newAttorneys = df_newAttorneys.rename(columns={"Firm_y": "Firm", "Registered as_y": "Registered as"}).reset_index(drop=True)
    df_changedFirms = df_changedFirms.rename(columns={"Firm_x": "Old firm", "Firm_y": "New firm"}).reset_index(drop=True)
    df_newAttorneys.index += 1
    df_changedFirms.index += 1

    return df_newAttorneys, df_changedFirms

def name_rank_df(df: pd.DataFrame, num: int) -> pd.DataFrame:
    """Make a dataframe of <num> rows ranked by name length"""
    df['Length'] = df['Name'].apply(lambda col: len(col))
    df.sort_values(by='Length', ascending=False, inplace=True)
    df.reset_index(inplace=True)
    df.index += 1
    return df.head(num)

def attorneys_df_to_lines(attorneys_df: pd.DataFrame) -> list[str]:
    """Convert a dataframe of attorneys to a list of strings to act as lines for display."""
    return [f"{attorney.Name}." if attorney.Firm == '' else f"{attorney.Name} of {attorney.Firm}." for attorney in attorneys_df.itertuples()]

def remove_tm_attorneys(attorneys_df: pd.DataFrame) -> pd.DataFrame:
    """Return a new dataframe with all the solely TM registered attorneys removed"""
    return attorneys_df.query("`Registered as` != 'Trade marks'")

def check_already_scraped(folderPath: Path) -> bool:
    filepaths = get_csv_filepaths(folderPath)
    [latestFilepath] = get_latest_csvs(filepaths, 1)
    date = str(datetime.date.today())
    return date == latestFilepath.stem