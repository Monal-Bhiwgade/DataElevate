from download import Download_data
import os
import load_data_api
import EDAerror
from sqlalchemy import create_engine
import pandas as pd
import sqlite3


class Load_data:
    @staticmethod
    def from_local(path):
        type = load_data_api.check_data_type(path)
        if "csv" == type:
            return load_data_api.from_csv(path)
        elif "excel" == type:
            return load_data_api.from_excel(path)
        elif "text" == type:
            return load_data_api.from_text(path)
        else:
            return EDAerror.Invalid_File_Support(path, "The file type is not supported.")

    @staticmethod
    def from_drive(url):
        Download_data.from_GoogleDrive.download_file(url)
        filename = Download_data.from_GoogleDrive.check_filename(url)
        path = os.getcwd()
        path = os.path.join(path, "GoogleDrive_Data")
        path = os.path.join(path, filename)
        return Load_data.from_local(path)
    @staticmethod
    def from_kaggle(url):
        path = Download_data.from_Kaggle.kaggle(url)
        if len(path) == 1:
            return Load_data.from_local(path[0])
        else:
            return EDAerror.MultipleFilesError(url)
        
    class Database: 
        # PostgreSQL connection function       
        def from_postgresql(db_name, table_name, user, password, host='localhost', port='5432'):
            connection_string = f'postgresql://{user}:{password}@{host}:{port}/{db_name}'
            engine = create_engine(connection_string)
            query = f"SELECT * FROM {table_name};"
            df = pd.read_sql(query, engine)
            return df

        # MySQL connection function
        def from_mysql(db_name, table_name, user, password, host='localhost', port='3306'):
            connection_string = f'mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db_name}'
            engine = create_engine(connection_string)
            query = f"SELECT * FROM {table_name};"
            df = pd.read_sql(query, engine)
            return df

        # MSSQL connection function
        def from_mssql(db_name, table_name, user, password, host='localhost', port='1433'):
            connection_string = f'mssql+pyodbc://{user}:{password}@{host}:{port}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server'
            engine = create_engine(connection_string)
            query = f"SELECT * FROM {table_name};"
            df = pd.read_sql(query, engine)
            return df

        # Oracle connection function
        def from_oracle(db_name, table_name, user, password, host='localhost', port='1521'):
            connection_string = f'oracle+cx_Oracle://{user}:{password}@{host}:{port}/{db_name}'
            engine = create_engine(connection_string)
            query = f"SELECT * FROM {table_name};"
            df = pd.read_sql(query, engine)
            return df

        # SQLite connection function
        def from_sqlite(db_name, table_name):
            conn = sqlite3.connect(db_name)  # SQLite uses a file-based database
            query = f"SELECT * FROM {table_name};"
            df = pd.read_sql(query, conn)
            conn.close()
            return df

        # MariaDB connection function
        def from_mariadb(db_name, table_name, user, password, host='localhost', port='3306'):
            connection_string = f'mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db_name}'  # MariaDB is compatible with MySQL
            engine = create_engine(connection_string)
            query = f"SELECT * FROM {table_name};"
            df = pd.read_sql(query, engine)
            return df

        # Amazon RDS connection function (MySQL/PostgreSQL)
        def from_amazon_rds(db_name, table_name, user, password, host, port='3306'):
            connection_string = f'mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db_name}'  # RDS typically uses MySQL or PostgreSQL
            engine = create_engine(connection_string)
            query = f"SELECT * FROM {table_name};"
            df = pd.read_sql(query, engine)
            return df

        # Azure SQL Database connection function
        def from_azure_sql(db_name, table_name, user, password, host='localhost', port='1433'):
            connection_string = f'mssql+pyodbc://{user}:{password}@{host}:{port}/{db_name}?driver=ODBC+Driver+17+for+SQL+Server'
            engine = create_engine(connection_string)
            query = f"SELECT * FROM {table_name};"
            df = pd.read_sql(query, engine)
            return df