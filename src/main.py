# start timer before anything else
#import timeit
#start_time = timeit.default_timer()

print 'Importing libraries ...'

from google.cloud import monitoring
from google.cloud.monitoring import Aligner
from googleapiclient import discovery
import google.auth
import os
from pandas import *
from datetime import *
import csv
import argparse

print 'Retrieving credentials ...'

parser = argparse.ArgumentParser()
parser.add_argument('-i', dest='project', default='kohls-mobile.json',
                    help='name of project credential file')
parser.add_argument('-t', dest='hours', default='24',
                    help='amount of hours to receive data from')
parser.add_argument('-a', dest='append', default='N',
                    help='merge instance name + first 3 digits of inst_id')
args = parser.parse_args()
hours = int(args.hours)
project_name = str(args.project)
append = args.append
if append == 'y' or append == 'Y':
    append = True
else:
    append = False
project_root = os.path.abspath(os.path.join(__file__, "../.."))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = project_root + os.path.sep + os.path.join('credentials', project_name)
credentials, project = google.auth.default()

resource_manager = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
compute = discovery.build('compute', 'v1', credentials=credentials)

instance_metrics = {'CPU Utilization': 'instance/cpu/utilization',  # concatenates with compute api base url
                    'Raw Disk Read Utilization': 'instance/disk/read_bytes_count',
                    'Raw Disk Write Utilization': 'instance/disk/write_bytes_count',
                    'Disk Read Operations': 'instance/disk/read_ops_count',
                    'Disk Write Operations': 'instance/disk/write_ops_count',
                    'Raw Net Received Utilization': 'instance/network/received_bytes_count',
                    'Raw Net Sent Utilization': 'instance/network/sent_bytes_count',
                    'Network Packets Received': 'instance/network/received_packets_count',
                    'Network Packets Sent': 'instance/network/sent_packets_count'}

total_metrics = {'Raw Disk Utilization': ('Disk', 'Utilization'),
                 'Disk Operations': ('Disk', 'Operations'),
                 'Raw Net Utilization': ('Net', 'Utilization'),
                 'Network Packets': ('Network', 'Packets')}

agent_metrics = {'Raw Mem Utilization': 'memory/bytes_used',
                 'Percent Memory Used': 'memory/percent_used',
                 'Raw Disk Space Usage': 'disk/bytes_used'}

models = []  # holds all default system configurations found in us-central1-a
instance_names = {}  # dict of instance id : instance name
available_instances = []  # list of all non-deleted instances by name
if hours > 1008:
    print 'only 1008 hours (6 weeks) or less of metrics can be collected (retrieving 1008)'
    hours = 1008


class UTC(tzinfo):
    """UTC"""
    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)

now_utc = datetime.now(tz=UTC())  # creates datetime object at closest 5 min increment UTC (GMT)
nearest_increment_utc = now_utc - timedelta(minutes=now_utc.minute % 5,
                                            seconds=now_utc.second,
                                            microseconds=now_utc.microsecond)


def get_monitoring_client(project):  # returns stackdriver monitoring Client object using project
    return monitoring.Client(project=project, credentials=credentials)


def main():
    instance_ids = {}  # dict of instance name : instance id
    specs = []  # holds list of configs for each instance
    atts = []  # holds list of attributes for each instance
    projects = api_call(resource_manager.projects(), 'projects', [])  # TODO Program untested with multiple projects
    print "Found %d projects" % len(projects)
    for project in projects:  # for each project in the list of project dictionaries :
        project['instances'] = []  # add another key : value pair into project dictionary
        project_id = project['projectId']
        try:
            m = api_call(compute.machineTypes(), 'items', {'project': project_id, 'zone': 'us-central1-a'})
        except:
            print 'No instances found.'
            return
        for model in m:
            models.append([model['name'], model['guestCpus'], model['memoryMb']])
        all_zones = api_call(compute.zones(), 'items', {'project': project_id})
        print "Found %d zones" % len(all_zones)
        disk_size = []
        print 'Loading instance attributes ...'
        for zone in all_zones:  # for each zone in list of zone dictionaries :
            zone_name = zone['name']
            current_instances = api_call(compute.instances(), 'items', {'project': project_id, 'zone': zone_name})
            if current_instances is not None and len(current_instances) > 0:
                project['instances'].extend(current_instances)
                # retrieve configs and store them in 'specs'
                for disk in api_call(compute.disks(), 'items', {'project': project_id, 'zone': zone_name}):  # loop through all disks to create a list
                    disk_size.append(disk['sizeGb'])
                for disk_index, instance_data in enumerate(current_instances):  # loop through all instances to create lists of their config
                    try:
                        os_version = compute.disks().get(project=project_id, zone=zone_name, disk=instance_data['name'])
                        os_version = os_version.execute()['sourceImage'].split('/')
                        os_version = os_version[len(os_version)-1]
                    except:
                        os_version = 'linux'
                    if 'windows' in os_version:
                        operating_system = 'Windows'
                    else:
                        operating_system = 'Linux'
                    if 'items' in instance_data['metadata'].keys():
                        metadata = instance_data['metadata']['items']
                    else:
                        metadata = ''
                    new_metadata = {}
                    group = ''
                    owner = ''
                    for data in metadata:  # take data with certain keys into variables, otherwise, if <250 characters, into new_metadata
                        if data['key'] == 'created-by':
                            group = data['value'].split('/')
                            group = group[len(group) - 1]
                        elif data['key'] == 'owner':
                            owner = data['value']
                        elif len(data['key']+data['value']) < 250:
                            new_metadata[str(data['key'])] = str(data['value'])
                    if new_metadata == {}:
                        new_metadata = ''
                    metadata = str(new_metadata).replace('"', '""')
                    if len(metadata) > 250:
                        metadata = ''
                    zone_loc = zone_name.split('-')[0]+'-'+zone_name.split('-')[1]
                    creation_date = instance_data['creationTimestamp']
                    instance_name = (instance_data['name'])
                    status = instance_data['status']
                    if status == 'RUNNING':
                        status = 'Running'
                    else:
                        status = 'Offline'
                    cpu_type = instance_data['cpuPlatform']
                    networkIP = instance_data['networkInterfaces'][0]['networkIP']
                    machineurl = instance_data['machineType']
                    instance_id = instance_data['id']
                    segments = machineurl.split('/')
                    machine_type = segments[len(segments) - 1]
                    cpus = get_cpus(machine_type)
                    ram = get_ram(machine_type)
                    benchmark = 29.9*float(cpus)
                    if append:
                        name_append = instance_name + '-' + instance_id[0:3]
                    else:
                        name_append = instance_name
                    specs.append([name_append, str(cpus), str(cpus), '1', '1', str(ram),
                                  'GCP', machine_type, str(benchmark), instance_id, cpu_type, '2600', operating_system, os_version])
                    atts.append([name_append, instance_id, networkIP, creation_date, group, owner, '"'+metadata+'"',
                                 zone_loc, zone_name, project_id, 'Google Cloud Platform', disk_size[disk_index], status])
                    instance_ids[instance_name] = instance_id
                    instance_names[instance_id] = instance_name
                    available_instances.append(instance_name)
        print "Found %d instances, retrieving %d hour(s) of metrics" % (len(project['instances']), hours)
        dict_metric = {}
        key_metric = []
        for key in sorted(instance_metrics):  # calls api for each metric, add to dict (metric : dataframe)
            df = (monitoring_call(project_id, key))
            if not df.empty:
                print key, "done"
                df = df.groupby(axis=1, level=0).sum()  # sum if duplicate headers
                if key == 'CPU Utilization':  # google output scale: 0-1, Densify import scale: 1-100
                    df *= 100
                else:  # google output measurement: per minute, Densify import measurement: per second
                    df /= 60
                dict_metric[key] = df

        for key in sorted(agent_metrics):  # calls api for each metric, add to dict (metric : dataframe)
            df = (monitoring_agent_call(project_id, key))
            if not df.empty:
                print key, "done"
                df = df.groupby(axis=1, level=0).sum()
                dict_metric[key] = df

        if len(dict_metric) > 0:
            for name in total_metrics:  # extrapolates total i/o from api metrics
                total = []
                for key in dict_metric:
                    if all(x in key for x in name):  # if key contains all of total_metrics tuple
                        total.append(dict_metric[key])
                dict_metric[name] = total[0].add(total[1], fill_value=0, level=0)

            for key in dict_metric:  # adds metric label to dataframe and converts dict to list
                df = dict_metric[key]
                key_label = [key] * df.shape[1]
                cols = list(zip(df.columns, key_label))
                df.columns = MultiIndex.from_tuples(cols)
                key_metric.append(df)

            sorted_metrics = concat(key_metric, axis=1).sort_index(axis=1, level=0)  # horizontal concat and sort by instance name
            gb = sorted_metrics.groupby(axis=1, level=0)  # group by instance name
            grouped_instances = [gb.get_group(x) for x in sorted(gb.groups)]  # create list of dataframe according to groupby
            dict_instances = {}
            for df in grouped_instances:
                inst_name = list(df)[0][0]
                if inst_name in instance_ids.keys():
                    instance_id = instance_ids[inst_name]
                    if append:
                        dict_instances[inst_name + '-' + instance_id[0:3]] = df  # create key:value pair of instance name : dataframe
                    else:
                        dict_instances[inst_name] = df
                df.columns = df.columns.droplevel()  # drop instance_name header
        try:
            final_list = concat(dict_instances, names=['host_name', 'Datetime'])  # vertical concat, names = index header
        except:
            final_list = DataFrame({"": []}) # empty dataframe
        if final_list.empty:
            print "No currently active instances"
        final_list.to_csv(path_or_buf=project_root + os.path.sep + 'workload.csv')

        # fill in inactive instances with empty data
        new_names = get_names(atts)
        for instance in new_names:
            atts.append([instance,'N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A'])
            specs.append([instance,'N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A'])

    to_csv_list(specs, 'gcp_config.csv', 'a')
    to_csv_list(atts, 'attributes.csv', 'b')


def api_call(base, key, args):  # generic method for pulling relevant data from api response
    return_res = []
    if args:
        request = base.list(**args)
    else:
        request = base.list()

    while request is not None:
        response = request.execute()
        if key in response:
            return_res.extend(response[key])
        request = base.list_next(previous_request=request, previous_response=response)
    return return_res


def monitoring_call(project_id, metric):  # hours = global variable parsed from discovery.bat
    client = get_monitoring_client(project_id)
    METRIC = 'compute.googleapis.com/' + instance_metrics[metric]
    query = client.query(METRIC, hours=hours, end_time=nearest_increment_utc)\
        .align(Aligner.ALIGN_MEAN, minutes=5)
    return query.as_dataframe(label='instance_name')


def monitoring_agent_call(project_id, metric):  # hours = global variable parsed from discovery.bat
    client = get_monitoring_client(project_id)
    METRIC = 'agent.googleapis.com/' + agent_metrics[metric]
    query = client.query(METRIC, hours=hours, end_time=nearest_increment_utc)\
        .align(Aligner.ALIGN_MEAN, minutes=5)
    try:
        frame = query.as_dataframe().filter(regex='used')
    except:
        return DataFrame({"": []})  # return empty dataframe
    column_names = list(frame) # list of tuples from multi-index (per column)
    for index, name in enumerate(sorted(column_names)):
        try:
            if instance_names[name[3]] in available_instances:
                column_names[index] = instance_names[name[3]]
            else:
                column_names[index] = ''
        except:
            print 'instance id', name[3], 'not valid'
    frame.columns = column_names
    return frame


def to_csv_list(lst, file_name, file_type):  # print any list of lists to a csv file
    with open(project_root + os.path.sep + file_name, 'wb') as f:
        if file_type == 'a':
            f.write('host_name,HW Total CPUs,HW Total Physical CPUs,HW Cores Per CPU,HW Threads Per Core,'
                    'HW Total Memory,HW Manufacturer,HW Model,BM CINT2006 Rate,HW Serial Number,'
                    'HW CPU Architecture,HW CPU Speed,OS Name,OS Version\n')
        if file_type == 'b':
            f.write('host_name,Instance ID,Instance IP,Launch Time, Instance Group, Instance Owner, Instance Tags,'
                    'Virtual Datacenter,Virtual Cluster,Virtual Domain,Virtual Technology,'
                    'PS Capacity,Power State\n')
        for item in lst:
            f.write(','.join(item)+'\n')
    f.close()


def get_cpus(model):  # function to retrieve amount of CPUs based on machine type from API
    if model.split('-')[0] == 'custom':
        return model.split('-')[1]
    for row in models:
        if row[0] == model:
            return row[1]


def get_ram(model):  # function to retrieve amount of RAM based on machine type from API
    if model.split('-')[0] == 'custom':
        return float(model.split('-')[2])
    for row in models:
        if row[0] == model:
            return row[2]


def get_names(attr):  # look through the workload csv to find instances that do not yet have set attributes (are inactive)
    with open(project_root + os.path.sep + 'workload.csv', 'rb') as f:
        reader = csv.reader(f)
        lst = (list(reader))
    f.close()
    new_names = []
    for metrics in range(1, len(lst), hours*12):
        instance_is_defined = False
        for instance in attr:
            if str(lst[metrics][0]) == str(instance[0]):
                instance_is_defined = True
                break
        if instance_is_defined is False:
            new_names.append(lst[metrics][0])
    return new_names


if __name__ == '__main__':
    main()

# display the final amount of time taken
#end_time = timeit.default_timer()
#program_time = end_time-start_time
#print 'Finished in', int(program_time), 'seconds'
