import csv
import os
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def read_and_convert_csv(file_path):
    data_columns = []

    try:
        with open(file_path, 'r') as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                while len(data_columns) < len(row):
                    data_columns.append([])

                for i, value in enumerate(row):
                    data_columns[i].append(value)

        # Convert each value from hex to decimal
        converted_data = {f"DataSet_{i+1}": [int(val, 16) if val else 0 for val in col] for i, col in enumerate(data_columns)}

        # Create a DataFrame from the converted data
        df = pd.DataFrame(converted_data)
        return df

    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None  # Return None in case of failure

def read_csv_to_dataframe(file_path):
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)

        # Check if the DataFrame has exactly two columns
        if df.shape[1] != 2:
            raise ValueError("The CSV file must have exactly two columns")

        return df

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except pd.errors.EmptyDataError:
        print(f"No data: {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def find_max_values(df):
    # Ensure the DataFrame has the expected number of columns
    if df.shape[1] != 2:
        raise ValueError("DataFrame must have exactly two columns")

    # Find the maximum value in each column
    max_col_1 = df.iloc[:, 0].max()
    max_col_2 = df.iloc[:, 1].max()

    # Find the overall maximum value between the two columns
    overall_max = max(max_col_1, max_col_2)

    return max_col_1, max_col_2, overall_max
