import pandas as pd
def check_data_type(path):
    if path.endswith(".csv"):
        return "csv"
    elif path.endswith(".xlsx") or path.endswith(".xls"):
        return "excel"
    elif path.endswith(".txt"):
        return "text"
    
@staticmethod
def from_csv(csv_file):
    csv_df = pd.read_csv(csv_file)
    return csv_df

@staticmethod
def from_excel(excel_file):
    excel_df = pd.read_excel(excel_file)
    return excel_df

@staticmethod
def from_text(text_file):
    with open(text_file, 'r') as file:
        first_line = file.readline()
    delimiter = '\t' if '\t' in first_line else ','
    text_df = pd.read_csv(text_file, sep=delimiter)
    return text_df
