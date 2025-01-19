class InvalidInput(Exception):
    """Raised when the provided Kaggle dataset URL or ID is invalid or inaccessible."""
    
    def __init__(self, url, message="The Kaggle dataset URL/ID is invalid or cannot be accessed."):
        self.url = url
        self.message = f"""{self.url} is invalid or cannot be accessed. {message}"""
        super().__init__(self.message)


class Invalid_Directory(Exception):
    """Raised when the specified directory does not exist."""
    
    def __init__(self, directory, message="The directory does not exist."):
        self.directory = directory
        self.message = f"""{self.directory} does not exist. {message}"""
        super().__init__(self.message)


class Invalid_File_Support(Exception):
    """Raised when the file type is not supported."""
    
    def __init__(self, file, message="Invalid File Support"):
        self.file = file
        self.message = f"""File: {self.file} is not supported.
        {message}."""
        super().__init__(self.message)


class MultipleFilesError(Exception):
    """Raised when multiple files are associated with a dataset URL or ID, and all files need to be downloaded."""
    
    def __init__(self, url=None, Id=None, message=None):
        self.file = url or Id
        if message is None:
            self.message = f"""There are multiple files associated with the given URL or dataset ID: {self.file}. 
Please download all files before attempting to load the data.  
To download the dataset, use the following method:  
`download.Kaggle.from_kaggle("<dataset-name>")`
"""
        else:
            self.message = message
        super().__init__(self.message)
