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
def plot_3d_heatmap(df):

    # Extracting X and Y values from the DataFrame
    # Pivot the DataFrame to create a matrix suitable for a heatmap
    heatmap_data = df.pivot_table(index=df.columns[1], columns=df.columns[0], aggfunc='size', fill_value=0)

    # Create the heatmap
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=heatmap_data.index
    ))

    fig.update_layout(title='Heatmap', xaxis_title=df.columns[0], yaxis_title=df.columns[1])
    fig.show()
