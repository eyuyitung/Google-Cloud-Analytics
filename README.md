# GCP Discovery

### Requirements
[Python 2.7.x](https://www.python.org/downloads/) (this program was written for 2.7.13 however)
Access to Cirba Analysis Console
## Getting Started
1. Ensure you have set your "Path" Environment Variable to the file location of your python installation 

2. Install the dependencies via pip. The dependencies used thus far are defined in the [requirements.txt](requirements.txt) file
```
pip install -r requirements.txt
```
3. Follow instructions in [Acquiring GCP credentials.docx](Acquiring GCP credentials.docx) to attain credentials for each project and
save them into the project root folder

if you wish to save this somewhere else or as a different name, make sure you update its location in the [main.py](main.py) file

## Loading GCP Attributes
1. Open up Cirba Analysis Console
2. Navigate to Administration > Packages and Components 
3. Click import custom packages and select [GCP_Based_Attributes.zip](GCP_Based_Attributes.zip) from the project root

## Usage
1. Run Discovery.bat as admin or utilize the Discovery as admin shortcut.
2. Specify the full credential filename of the project from which you want to pull data.
3. Enter the # of hours you would like to sample. 
4. Specify whether or not and of the instances in the project contain active Stackdriver Agents.
5. Open Cirba Analysis Console and ensure the data has loaded properly.

## Notes
The timeframe of the dataset begins n hours back from 23:55 UTC yesterday with samples every 5 minutes

