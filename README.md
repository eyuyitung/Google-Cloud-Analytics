# Google cloud scraper

## Getting Started
1. Install the dependencies via pip. The dependencies used thus far are defined in the [requirements.txt](requirements.txt) file
```
pip install -r requirements.txt
```

2. Download a set of google credentials from the online api console [link](https://console.developers.google.com/apis/credentials). Make sure that you get a **service** credential account.
Save this file in the root of this project as `google-credentials.json` 

if you wish to save this somewhere else or as a different name, make sure you update its location in the [main.py](main.py) file

## Usage

The main entry point to this script is in the `main.py` file
To run the program enter the following in the command line from the root project directory. 
```
python src\main.py 
```