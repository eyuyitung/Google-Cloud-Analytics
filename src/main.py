from googleapiclient import discovery
from google.cloud import monitoring
import google.auth
import os
import pprint

project_root = os.getcwd()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = project_root + "\\google-credentials.json"

credentials, project = google.auth.default()

rm = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
comp = discovery.build('compute', 'v1', credentials=credentials)

def get_monitoring_client(project) :
    return monitoring.Client(project = project,credentials=credentials)




def main():
    proreq = rm.projects().list()
    prores = proreq.execute()
    proarr = prores['projects'][0]
    project_name = proarr['name']
    project_id = proarr['projectId']
    zonereq = comp.zones().list(project=project_id)
    zoneres = zonereq.execute()
    instances = []
    for zone in zoneres['items']:
        zone_name = zone['name']
        instreq = comp.instances().list(project=project_id, zone=zone_name)
        instres = instreq.execute()
        if 'items' in instres:
            client = get_monitoring_client(project_id,zone = zone_name)
            METRIC = 'compute.googleapis.com/instance/cpu/utilization'
            query =(client.query(METRIC,minutes= 5))
            print(query.as_dataframe())
            instance_name = (instres['items'][0]['name'])
            status = (instres['items'][0]['status'])
            machineurl = instres['items'][0]['machineType']
            machineType = ""
            for key in machineurl:
                if key == '/':
                    machineType = ""
                else:
                    machineType += key
            instances.append({'project name': project_name,
                              'zone name': zone_name,
                              'active instances': instance_name,
                              'instance status': status,
                               'machine type': machineType})

        else: instances.append(zone_name)
    pprint.pprint(instances)
if __name__ == '__main__':
    main()
