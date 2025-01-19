# DataQuest

**DataQuest** is a Python library designed to streamline the process of downloading, loading, and extracting data from various sources such as Google Drive, Kaggle, and local archives. It simplifies working with data files, enabling developers and analysts to focus on their data analysis tasks.

---

## Features

- **Download Data**: 
  - Easily download files from Google Drive and Kaggle.
- **Load Data**: 
  - Load data directly from CSV, Excel, text, or other supported file formats.
- **Extract Archives**:
  - Extract files from compressed archives (e.g., `.zip`, `.tar`, `.gz`).

---

## Installation

Install the package using pip:

```bash
pip install dataquest
```

---

## Quickstart

Here's how to get started with DataQuest:

### 1. Import the Library

```python
from dataquest import Download_data, Load_data, Extractor
```

## 2. Download Data

### `GoogleDrive`
Downloads a files/ folders from Google Drive.

### File download
```python
Download_data.GoogleDrive.download_file(url/ file_id: str, destination: str) #destination: Optional
```

### Folder download
```python 
Download_data.GoogleDrive.download_folder(url/ file_id: str, destination: str) #destination: Optional
```

### Check FileName
```python
Download_data.GoogleDrive.check_filename(url/ file_id: str)
```

### Get Id of file
```python
Download_data.GoogleDrive.get_file_id(url : str)
```

### Kaggle

```python
# Provide Kaggle dataset path and destination
Download_data.Kaggle.from_kaggle(dataset="kaggle-dataset-URL", destination="path/to/save") #destination: Optional
```

## 3. Load Data

### From Local  (CSV, Text, Excel)

```python
data = Load_data.from_local("path/to/your_file")
```
### From Kaggle

```python
data = Load_data.from_kaggle(url = "kaggle-dataset-URL")
```

### From Drive (Under Maintenance)

```python
data = Load_data.from_drive(url = "dataset url from drive")
```

### From Database (Under Maintenance)

#### Supported Databases
The following databases are supported:
- PostgreSQL
- MySQL
- Microsoft SQL Server (MSSQL)
- Oracle
- SQLite
- MariaDB
- Amazon RDS
- Azure SQL

#### Usage Examples

### Loading Data from PostgreSQL (Under Maintenance)
To load data from a PostgreSQL database, use the `from_postgresql` method:
```python
data = Load_data.Database.from_postgresql(
    db_name='your_database_name',
    table_name='your_table_name',
    username='your_username',
    password='your_password',
    host='your_host',
    port='your_port'
)
```
### Loading Data from SQLite (Under Maintenance)
To load data from an SQLite database, use the sqlite method:

```python
data = Load_data.Database.sqlite(
    db_name='your_database_name',
    table_name='your_table_name'
)
```
### Generalized Syntax for Other Databases (Under Maintenance)

```python 
data = Load_data.Database.DataBase_Type(
    db_name='your_database_name',
    table_name='your_table_name',
    username='your_username',
    password='your_password',
    host='your_host',
    port='your_port'
)
```
### Example
```python
data = Load_data.Database.from_mysql(
    db_name='your_database_name',
    table_name='your_table_name',
    username='your_username',
    password='your_password',
    host='your_host',
    port='your_port'
)
```

## 4. Extract Archives

```python
Extractor.extract_archive("path/to/your_archive.zip", destination="path/to/extract") destination: Optional
```

---


## Contributing

Contributions are welcome! Feel free to submit a pull request or raise issues for any bugs or feature requests.

---

## License

This project is licensed under the Apache License 2.0.
See the LICENSE file for more details.

---

## Author

**Name:** Moanl Bhiwgade 
**Email:** 3051monal@gmail.com  
**Version:** 1.0.0
