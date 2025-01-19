from setuptools import setup, find_packages
setup(
    name="DataQuest",
    version="1.0.0",
    author="Monal Bhiwgade",
    author_email="3051monal@gmail.com",
    description="DataQuest is a Python library designed to simplify and enhance data management and analysis workflows. It offers tools for seamless data access, transformation, and integration with external services like Google Drive, ensuring security and ease of use.",
    long_description="© 2025 DataQuest. All rights reserved.",
    long_description_content_type="text/plain",
    url="https://github.com/Monal-Bhiwgade/DataQuest",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache License 2.0",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
