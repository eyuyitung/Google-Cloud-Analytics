from google.cloud import monitoring
from google.cloud.monitoring import Aligner
from googleapiclient import discovery
import google.auth
import os
import pandas
import csv
import json
from pprint import pprint



project_root = os.path.abspath(os.path.join(__file__ ,"../.."))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = project_root + os.path.sep + "google-credentials.json"

credentials, project = google.auth.default()

resource_manager = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
compute = discovery.build('compute', 'v1', credentials=credentials)

instance_metrics = {'cpu utilization': 'instance/cpu/utilization',  # concatenates with compute api base url
                    'disk read bytes': 'instance/disk/read_bytes_count',
                    'disk read operations': 'instance/disk/read_ops_count',
                    'disk write bytes': 'instance/disk/write_bytes_count',
                    'disk write operations': 'instance/disk/write_ops_count',
                    'received bytes': 'instance/network/received_bytes_count',
                    'received packets': 'instance/network/received_packets_count',
                    'sent bytes': 'instance/network/sent_bytes_count',
                    'sent packets': 'instance/network/sent_packets_count'}


def get_monitoring_client(project):
    return monitoring.Client(project=project, credentials=credentials)


def main():
    specs = []
    data = {} # TODO dump project list back into data dict
    data['projects'] = api_call(resource_manager.projects(), 'projects', [])
    print "Found %d projects" % len(data['projects'])
    for project in data['projects']:  # for each project in the list of project dictionaries :
        project['instances'] = []  # add another key : value pair into project dictionary
        project_id = project['projectId']

        all_zones = api_call(compute.zones(), 'items', {'project': project_id})
        print "Found %d zones" % len(all_zones)
        for zone in all_zones:  # for each zone in list of zone dictionaries :
            zone_name = zone['name']
            current_instances = api_call(compute.instances(), 'items', {'project': project_id, 'zone': zone_name})
            if current_instances is not None and len(current_instances) > 0:
                project['instances'].extend(current_instances)
                count = 0
                gigs = []
                for i in api_call(compute.disks(), 'items', {'project': project_id, 'zone': zone_name}):
                    #print i
                    gigs.append(i['sizeGb'])
                for i in current_instances:
                    #print i
                    #print(api_call(compute.disks(), 'items', {'project': project_id, 'zone': zone_name}))
                    instance_name = (i['name'])
                    cpuType = i['cpuPlatform']
                    networkIP = i['networkInterfaces'][0]['networkIP']
                    machineurl = i['machineType']
                    id = i['id']
                    segments = machineurl.split('/')
                    machineType = segments[len(segments) - 1]
                    #print(compute.disks().list(project=project_id, zone=zone_name).execute()['items'][])
                        #disk = item['name']+' '+item['sizeGb']
                    print compute.instances().get(project=project_id, zone=zone_name, instance=instance_name).execute()['networkInterfaces']
                    specs.append([id,project_id,zone_name,instance_name,machineType,cpuType,str(get_cpus(machineType)),str(get_ram(machineType)),gigs[count],networkIP])
                    count+=1
        print "Found %d instances" % len(project['instances'])
        for instance in project['instances']:  # TODO Associate metrics with respective instance

            instance['metrics'] = []
            #for key in sorted(instance_metrics):
            #    instance['metrics'].append(monitoring_call(project_id, key, instance['name']))
            #project['metrics'] = pandas.concat(instance['metrics'], axis=1)
           # project['metrics'].to_csv('out.csv')  #TODO Add column headers for each data set
                                                  #TODO Set end time interval to when the program executes
    #to_csv_dict([{'ya':'yahoo','yay':'yep'},{'good':'cool','great':'i know','sure':'really'},{'good':'cool','great':'i know','sure':'really'}],'mycsvfile.csv')
    #to_csv_list([['cow','bird'],['monkey','horse','fish']],'mycsvfile.csv')
    #print read_csv('mycsvfile.csv')
    #print get_ram('n1-highcpu-2')
    #pprint(specs)
    to_csv_list(specs,'specs.csv')


def api_call(base, key, args):  # generic method for pulling relevant data from api response
    export = []
    if args:
        request = base.list(**args)
    else:
        request = base.list()

    while request is not None:
        response = request.execute()
        if key in response:
            export.extend(response[key])
        request = base.list_next(previous_request=request, previous_response=response)
    return export


def monitoring_call(project_id, metric, instance_name):
    client = get_monitoring_client(project_id)
    METRIC = 'compute.googleapis.com/' + instance_metrics[metric]
    query = client.query(METRIC, hours=24)\
        .select_metrics(instance_name=instance_name)\
        .align(Aligner.ALIGN_MEAN, minutes=5) #TODO average every 5 min
    return query.as_dataframe()

def to_csv_dict(dict,file):
        # file = open('test.csv','w')
        # for item in dict:
        #    file.write(','.join(item))
        #    file.write('\n')
        # file.close()
    with open(file, 'wb') as f:
        for item in dict:
            w = csv.DictWriter(f, item.keys())
            w.writerow(item)
    f.close()

def to_csv_list(lst,file):
    with open(file, 'wb') as f:
        f.write('instance id:,project:,zone:,instance:,model:,cpu type:,cpus:,memory(GB):,storage(GB):,network ip:\n')
        for item in lst:
            f.write(','.join(item)+'\n')
    f.close()

def read_csv(file):
    with open(file, 'rb') as f:
        reader = csv.reader(f)
        lst = (list(reader))
    f.close()
    return lst

def get_cpus(model):
    if model.split('-')[0] == 'custom':
        return model.split('-')[1]
    with open('gcp_models.csv', 'rb') as f:
        reader = csv.reader(f)
        lst = (list(reader))
    f.close()
    for row in lst:
        if row[0] == model:
            return row[2]
    return 'n/a'

def get_ram(model):
    if model.split('-')[0] == 'custom':
        return float(model.split('-')[2])/1024
    with open('gcp_models.csv', 'rb') as f:
        reader = csv.reader(f)
        lst = (list(reader))
    f.close()
    for row in lst:
        if row[0] == model:
            return row[3]
    return 'n/a'

                # def get_disk(project_id, zone, instance):


if __name__ == '__main__':
    main()