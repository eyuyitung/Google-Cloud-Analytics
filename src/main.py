#start timer before anything else
print 'Importing assets ...'
import timeit
start_time=timeit.default_timer()

from google.cloud import monitoring
from google.cloud.monitoring import Aligner
from googleapiclient import discovery
from pprint import pprint
import google.auth
import os
import pandas
from datetime import *
import csv

print 'Retrieving credentials ...'
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

with open(project_root + os.path.sep + 'gcp_models.csv', 'rb') as f:
    reader = csv.reader(f)
    models_list = (list(reader))
f.close()

models = []

class UTC(tzinfo):
    """UTC"""
    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)

midnight_utc = time(0, tzinfo=UTC()) #because time 0 = midnight yesterday
yesterday_midnight_utc = datetime.combine(date.today(), midnight_utc)

def get_monitoring_client(project):
    return monitoring.Client(project=project, credentials=credentials)


def main():
    specs = []#holds list of configs for each instance
    atts = []#holds list of attributes for each instance
    data = {}# TODO dump project list back into data dict
    data['projects'] = api_call(resource_manager.projects(), 'projects', [])
    print "Found %d projects" % len(data['projects'])
    for project in data['projects']:  # for each project in the list of project dictionaries :
        project['instances'] = []  # add another key : value pair into project dictionary
        project_id = project['projectId']
        m = api_call(compute.machineTypes(), 'items', {'project': project_id, 'zone': 'us-central1-a'})
        for model in m:
            models.append([model['name'],model['guestCpus'],model['memoryMb']])
        #pprint (api_call(compute.machineTypes(), 'items', {'project': project_id, 'zone': 'us-central1-a'}))
        all_zones = api_call(compute.zones(), 'items', {'project': project_id})
        print "Found %d zones" % len(all_zones)
        disk_size = []
        print 'Loading instances ...'
        for zone in all_zones:  # for each zone in list of zone dictionaries :
            zone_name = zone['name']
            current_instances = api_call(compute.instances(), 'items', {'project': project_id, 'zone': zone_name})
            if current_instances is not None and len(current_instances) > 0:
                project['instances'].extend(current_instances)

                #retrieve configs and store them in 'specs'
                disk_index = 0
                for disk in api_call(compute.disks(), 'items', {'project': project_id, 'zone': zone_name}):#loop through all disks to create a list
                    disk_size.append(disk['sizeGb'])
                for i in current_instances:#loop through all instances to create lists of their configs
                    zone_loc = zone_name.split('-')[0]+'-'+zone_name.split('-')[1]
                    zone_dep = zone_name.split('-')[2]
                    creation_date = i['creationTimestamp']
                    instance_name = (i['name'])
                    status = i['status']
                    cpu_type = i['cpuPlatform']
                    networkIP = i['networkInterfaces'][0]['networkIP']
                    machineurl = i['machineType']
                    id = i['id']
                    segments = machineurl.split('/')
                    machine_type = segments[len(segments) - 1]
                    cpus = get_cpus(machine_type)
                    ram = get_ram(machine_type)
                    specs.append([instance_name,str(cpus),str(cpus),'1','1','',
                                  '',str(ram),'Google',machine_type,id,cpu_type])
                    atts.append([instance_name,id,networkIP,creation_date,zone_loc,zone_dep,disk_size[disk_index]])
                    disk_index+=1

    #collect metrics for each instance, append to dataframe, and merge all dataframes to one csv
        print "Found %d instances" % len(project['instances'])
        project['metrics'] = []
    to_csv_list(specs, 'gcp_config.csv','a')
    to_csv_list(atts, 'attributes.csv','b')

    #display the final amount of time taken
    end_time = timeit.default_timer()
    program_time = end_time-start_time
    print 'Finished in',int(program_time), 'seconds'
        #TODO Add column headers for each data set
        #TODO Set end time interval to when the program executes


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


def monitoring_call(project_id, metric, instance_name):  #
    client = get_monitoring_client(project_id)
    METRIC = 'compute.googleapis.com/' + instance_metrics[metric]
    query = client.query(METRIC, hours=24, end_time=yesterday_midnight_utc)\
        .select_metrics(instance_name=instance_name)\
        .align(Aligner.ALIGN_MEAN, minutes=5)
    return query.as_dataframe()

#print ant list of lists to a csv file
def to_csv_list(lst,file,type):
    with open(project_root + os.path.sep + file, 'wb') as f:
        if type == 'a':
            f.write('host_name,HW Total CPUs,HW Total Physical CPUs,HW Cores Per CPU,HW Threads Per Core,BM CINT2006 Rate,'
                    'HW CPU Speed,HW Total Memory,HW Manufacturer,HW Model,HW Serial Number,HW CPU Architecture\n')
        if type == 'b':
            f.write('host_name,Instance ID,Instance IP,'
                    'Launch Time,Location,Department,PS Capacity\n')
        for item in lst:
            f.write(','.join(item)+'\n')
    f.close()

def get_cpus(model):
    if model.split('-')[0] == 'custom':
        return model.split('-')[1]
    for row in models:
        if row[0] == model:
            return row[1]

def get_ram(model):
    if model.split('-')[0] == 'custom':
        return float(model.split('-')[2])
    for row in models:
        if row[0] == model:
            return row[2]


if __name__ == '__main__':
    main()