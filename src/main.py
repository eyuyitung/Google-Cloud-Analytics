#start timer before anything else
import timeit
start_time=timeit.default_timer()

print 'Importing libraries ...'

from google.cloud import monitoring
from google.cloud.monitoring import Aligner
from googleapiclient import discovery
from pprint import pprint
import google.auth
import os
from pandas import *
from datetime import *
import csv
import argparse

print 'Retrieving credentials ...'
project_root = os.path.abspath(os.path.join(__file__ ,"../.."))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = project_root + os.path.sep + "google-credentials.json"

credentials, project = google.auth.default()

resource_manager = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
compute = discovery.build('compute', 'v1', credentials=credentials)

instance_metrics = {'CPU Utilization': 'instance/cpu/utilization',  # concatenates with compute api base url
                    'Raw Disk Read Utilization': 'instance/disk/read_bytes_count',
                    'Disk Read Operations': 'instance/disk/read_ops_count',
                    'Raw Disk Write Utilization': 'instance/disk/write_bytes_count',
                    'Disk Write Operations': 'instance/disk/write_ops_count',
                    'Raw Net Received Utilization': 'instance/network/received_bytes_count',
                    'Network Packets Received': 'instance/network/received_packets_count',
                    'Raw Net Sent Utilization': 'instance/network/sent_bytes_count',
                    'Network Packets Sent': 'instance/network/sent_packets_count'}

with open(project_root + os.path.sep + 'gcp_models.csv', 'rb') as f:
    reader = csv.reader(f)
    models_list = (list(reader))
f.close()

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-t', dest = 'hours',
                    help='amount of hours to receive data from')
args = parser.parse_args()
hours = args.hours
if hours:
    hours = int(args.hours)
else:
    hours = 24
#if hours > 168:
#    print 'only 168 hours or less of metrics can be collected (retreiving 168)'
#    hours = 168

models = []

class UTC(tzinfo):
    """UTC"""
    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)

yesterday_midnight_utc = datetime.combine(date.today(), time(0, tzinfo=UTC())) #because time 0 = midnight yesterday

def get_monitoring_client(project):
    return monitoring.Client(project=project, credentials=credentials)


def main():
    specs = []#holds list of configs for each instance
    atts = []#holds list of attributes for each instance
    projects = api_call(resource_manager.projects(), 'projects', [])
    print "Found %d projects" % len(projects)
    for project in projects:  # for each project in the list of project dictionaries :
        project['instances'] = []  # add another key : value pair into project dictionary
        project_id = project['projectId']
        m = api_call(compute.machineTypes(), 'items', {'project': project_id, 'zone': 'us-central1-a'})
        for model in m:
            models.append([model['name'],model['guestCpus'],model['memoryMb']])
        #pprint (api_call(compute.machineTypes(), 'items', {'project': project_id, 'zone': 'us-central1-a'}))
        all_zones = api_call(compute.zones(), 'items', {'project': project_id})
        print "Found %d zones" % len(all_zones)
        disk_size = []
        name_instance = []
        print 'Loading instance attributes ...'
        for zone in all_zones:  # for each zone in list of zone dictionaries :
            zone_name = zone['name']
            current_instances = api_call(compute.instances(), 'items', {'project': project_id, 'zone': zone_name})
            if current_instances is not None and len(current_instances) > 0:
                #print zone_name
                #print compute.instanceGroups().list(project=project_id, zone=zone_name).execute()
                #print compute.instanceGroups().get(project=project_id, zone=zone_name, instanceGroup='auto-scaling-group-1').execute()
                project['instances'].extend(current_instances)

                #  retrieve configs and store them in 'specs'
                disk_index = 0
                for disk in api_call(compute.disks(), 'items', {'project': project_id, 'zone': zone_name}):  # loop through all disks to create a list
                    disk_size.append(disk['sizeGb'])
                for i in current_instances:  # loop through all instances to create lists of their configs
                    os_version = compute.disks().get(project=project_id, zone=zone_name, disk=i['name']).execute()['sourceImage'].split('/')
                    os_version = os_version[len(os_version)-1]
                    if 'windows' in os_version:
                        operating_system = 'Windows'
                    else:
                        operating_system = 'Linux'
                    if 'items' in i['metadata'].keys():
                        metadata = i['metadata']['items']
                    else:
                        metadata = ''
                    new_metadata = {}
                    group = ''
                    for data in metadata:
                        if 'created-by' in new_metadata.keys():
                            group = new_metadata['created-by'].split('/')
                            group = group[len(group) - 1]
                        else:
                            new_metadata[str(data['key'])]=str(data['value'])
                    if new_metadata == {}:
                        new_metadata = ''
                    metadata = str(new_metadata).replace('"','""')
                    #print compute.instances().get(project=project_id, zone=zone_name, instance=i['name']).execute()['metadata']
                    zone_loc = zone_name.split('-')[0]+'-'+zone_name.split('-')[1]
                    creation_date = i['creationTimestamp']
                    instance_name = (i['name'])
                    status = i['status']
                    if status == 'RUNNING':
                        status = 'Running'
                    else:
                        status = 'Offline'
                    cpu_type = i['cpuPlatform']
                    networkIP = i['networkInterfaces'][0]['networkIP']
                    machineurl = i['machineType']
                    id = i['id']
                    segments = machineurl.split('/')
                    machine_type = segments[len(segments) - 1]
                    cpus = get_cpus(machine_type)
                    ram = get_ram(machine_type)
                    specs.append([instance_name, str(cpus), str(cpus), '1', '1', str(ram), 'GCP', machine_type, id, cpu_type, operating_system, os_version])
                    atts.append([instance_name, id, networkIP, creation_date, group, '"'+metadata+'"',# TODO metadata is too long to push to CIRBA
                                 zone_loc, zone_name, project_id, 'Google Cloud Platform', disk_size[disk_index], status])
                    disk_index += 1
                    if i['status'] != 'TERMINATED':
                        name_instance.append(instance_name)

        print "Found %d instances, retrieving %d hour(s) of metrics" % (len(project['instances']),hours)
        key_metric = []
        for key in sorted(instance_metrics):
            df = (monitoring_call(project_id, key))
            print key, "done"
            if df.shape[1] > len(name_instance): #  if instance has more than 1 value for metric, finds aggergate
                df = df.groupby(axis=1, level=0).sum()
            if key == 'CPU Utilization':
                df *= 100
            key_label = [key] * df.shape[1]
            cols = list(zip(df.columns, key_label))
            df.columns = MultiIndex.from_tuples(cols)
            key_metric.append(df)

        sorted_metrics = concat(key_metric, axis=1).sort_index(axis=1, level=0)
        gb = sorted_metrics.groupby(axis=1, level=0)
        grouped_instances = [gb.get_group(x) for x in sorted(gb.groups)]
        dict_instances = {}
        for df in grouped_instances:
            dict_instances[list(df)[0][0]] = df
            df.columns = df.columns.droplevel()

        final_list = concat(dict_instances, names=['host_name', 'Datetime'])
        final_list.to_csv(path_or_buf=project_root + os.path.sep + 'workload.csv')

    to_csv_list(specs, 'gcp_config.csv','a')
    to_csv_list(atts, 'attributes.csv','b')
    # display the final amount of time taken
    end_time = timeit.default_timer()
    program_time = end_time-start_time
    print 'Finished in',int(program_time), 'seconds'


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


def monitoring_call(project_id, metric):  #
    client = get_monitoring_client(project_id)
    METRIC = 'compute.googleapis.com/' + instance_metrics[metric]
    query = client.query(METRIC, hours=hours, end_time=yesterday_midnight_utc)\
        .align(Aligner.ALIGN_MEAN, minutes=5)
    return query.as_dataframe(labels=['instance_name'])


# print ant list of lists to a csv file
def to_csv_list(lst,file,type):
    with open(project_root + os.path.sep + file, 'wb') as f:
        if type == 'a':
            f.write('host_name,HW Total CPUs,HW Total Physical CPUs,HW Cores Per CPU,HW Threads Per Core,'
                    'HW Total Memory,HW Manufacturer,HW Model,HW Serial Number,HW CPU Architecture,OS Name,OS Version\n')
        if type == 'b':
            f.write('host_name,Instance ID,Instance IP,Launch Time, Group, Tags,'
                    'Virtual Datacenter,Virtual Cluster,Virtual Domain,Virtual Technology,'
                    'PS Capacity,Power State\n')
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