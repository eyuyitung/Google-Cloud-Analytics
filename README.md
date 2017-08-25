# GCP Discovery

### Requirements
[Python 2.7.x](https://www.python.org/downloads/) (this program was written for 2.7.13 however)

Access to Cirba Analysis Console
## Getting Started

1. Install the dependencies via pip. The dependencies used thus far are defined in the [requirements.txt](requirements.txt) file
```
pip install -r requirements.txt
```
2. Follow instructions in [Acquiring GCP credentials.docx](Acquiring GCP credentials.docx) to attain credentials for each project and
save them into the project root folder

## Loading GCP Attributes
1. Open up Cirba Analysis Console
2. Navigate to Administration > Packages and Components 
3. Click import custom packages and select [GCP_Based_Attributes.zip](GCP_Based_Attributes.zip) from the project root

## Usage
1. Edit the PYDIR parameter in [Discovery.bat](Discovery.bat) to be the path to your Python.exe file. (default : C:\Python27\Python.exe)
2. Open an administator instance of command prompt and navigate to the project folder
3. enter the command ``` discovery ``` and add any of the following :
	1. pass in ``` -a ``` or ``` --auto ``` to load all projects in the credentials folder 
		using the default parameters specified in Discovery.bat
	2. pass in ``` -f ``` or ``` --file ``` with a credential file ex. (my-project.json) to
		load that project using the default parameters. 
	3. pass in no arguments to specifiy all of the parameters manually 		
4. Open Cirba Analysis Console and ensure the data has loaded properly.

## Notes
The timeframe of the dataset begins by default, n hours back from 23:55 UTC yesterday with samples every 5 minutes however changing the 
midnight parameter in [Discovery](Discovery.bat) to N, which will cause it to sample from the nearest 5 minute increment instead.
