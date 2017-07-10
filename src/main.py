from googleapiclient import discovery
import google.auth
import os

project_root = os.getcwd()
os.environ ["GOOGLE_APPLICATION_CREDENTIALS"] = project_root + "\\google-credentials.json"

credentials, project = google.auth.default()

rm = discovery.build('cloudresourcemanager', 'v1',credentials=credentials)

comp = discovery.build('compute', 'v1', credentials=credentials)

def main() :
    project = rm.projects().list().execute()
    print project['projects'][0]['projectId']
    zone = comp.zones().list({project['projects'][0]['projectId'][0]}).execute()
#  print zone


if __name__ == '__main__':
    main()
