from googleapiclient import discovery
from google.cloud import monitoring
import google.auth
import os
import pprint
import json

project_root = os.getcwd()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = project_root + os.path.sep + "google-credentials.json"

credentials, project = google.auth.default()

rm = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
comp = discovery.build('compute', 'v1', credentials=credentials)

def get_monitoring_client(project) :
    return monitoring.Client(project = project,credentials=credentials)

def main():
    project_req = rm.projects().list()
    project_res = project_req.execute()
    projects = project_res['projects']
    project = projects[0]
    project_name = project['name']
    project_id = project['projectId']
    zone_req = comp.zones().list(project=project_id)
    zone_res = zone_req.execute()
    instances = []
    for zone in zone_res['items']:
        zone_name = zone['name']
        instance_req = comp.instances().list(project=project_id, zone=zone_name)
        instance_res = instance_req.execute()
        if 'items' in instance_res:
            instance_name = (instance_res['items'][0]['name'])
            status = (instance_res['items'][0]['status'])
            machineurl = instance_res['items'][0]['machineType']
            segments = machineurl.split('/')
            machineType = segments[len(segments) - 1]
            instances.append({'project name': project_name,
                              'zone name': zone_name,
                              'active instances': instance_name,
                              'instance status': status,
                               'machine type': machineType})

        else: instances.append(zone_name)
    pprint.pprint(instances)
    client = get_monitoring_client(project_id)
    METRIC = 'compute.googleapis.com/instance/cpu/utilization'
    query = (client.query(METRIC, minutes=5))
    print(query.as_dataframe())
if __name__ == '__main__':
    main()
