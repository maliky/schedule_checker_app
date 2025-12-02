from setuptools import setup, find_packages

setup(
    name="class_schedule",
    version="0.1.0",
    author="mlk",
    description="A data wrangling package for processing and analyzing class schedules.",
    long_description=open("README.org").read(),
    long_description_content_type="text/plain",
    packages=find_packages(include=["class_schedule", "class_schedule.*"]),
    include_package_data=True,
    install_requires=[
        "pandas",
        "altair",
        "openpyxl",
        "python-dotenv",
        "numpy",
    ],
    python_requires=">=3.11",
)
