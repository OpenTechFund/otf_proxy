"""
Utilities for log reporting
Used by command line and flask app
"""
import re
import os
import datetime
import logging
from dotenv import load_dotenv
from simple_AWS.s3_functions import *
import sqlalchemy as db
from system_utilities import get_configs

logger = logging.getLogger('logger')

def analyze_file(raw_data, domain):
    """
    Analyzes the raw data from the file - for status, agents and pages
    :arg: raw_data
    :returns: dict of dicts
    """
    domain_data = get_domain_data(domain)

    if domain_data['paths_ignore']:
        paths_ignore_list = domain_data['paths_ignore'].split(',')
    else:
        paths_ignore_list = False
    if domain_data['ext_ignore']:
        exts_ignore_list = domain_data['ext_ignore'].split(',')
        
    raw_data_list = raw_data.split('\n')
    if len(raw_data_list) < 5: # Not worth analyzing
        return False
    analyzed_log_data = {
            'visitor_ips': {},
            'status': {},
            'user_agent': {},
            'pages_visited' : {}
        }
    analyzed_log_data['hits'] = len(raw_data_list)
    log_date_match = re.compile('[0-9]{2}[\/]{1}[A-Za-z]{3}[\/]{1}[0-9]{4}[:]{1}[0-9]{2}[:]{1}[0-9]{2}[:]{1}[0-9]{2}')
    log_status_match = re.compile('[\ ]{1}[0-9]{3}[\ ]{1}')
    log_ip_match = re.compile('[0-9]{1,3}[\.]{1}[0-9]{1,3}[\.]{1}[0-9]{1,3}[\.]{1}[0-9]{1,3}')
    datetimes = []
    for line in raw_data_list:
        has_ips = True
        log_data = {}
        line_split = line.split(' ')
        try:
            log_data['ip'] = log_ip_match.search(line_split[0]).group(0)
        except:
            has_ips = False
        try:
            log_data['datetime'] = log_date_match.search(line).group(0)
            log_data['status'] = log_status_match.search(line).group(0)
        except:
            continue
        datetimes.append(datetime.datetime.strptime(log_data['datetime'], '%d/%b/%Y:%H:%M:%S'))
        try:
            log_data['user_agent'] = line.split(' "')[-1]
        except:
            continue
        try:
            log_data['page_visited'] = line.split(' "')[-3].split(' ')[1]
        except:
            continue
        if exts_ignore_list:
            ext_ignore = False
            for ext in exts_ignore_list:
                if ext in log_data['page_visited']:
                    ext_ignore = True
            if ext_ignore:
                continue
        if paths_ignore_list:
            should_skip = False
            for ignore in paths_ignore_list:
                if ignore in log_data['page_visited']:
                    should_skip = True
            if should_skip:
                continue
        
        if 'ip' in log_data:
            if log_data['ip'] in analyzed_log_data['visitor_ips']:
                analyzed_log_data['visitor_ips'][log_data['ip']] += 1
            else:
                analyzed_log_data['visitor_ips'][log_data['ip']] = 1
        if log_data['status'] in analyzed_log_data['status']:
            analyzed_log_data['status'][log_data['status']] += 1
        else:
            analyzed_log_data['status'][log_data['status']] = 1
        if log_data['user_agent'] in analyzed_log_data['user_agent']:
            analyzed_log_data['user_agent'][log_data['user_agent']] += 1
        else:
            analyzed_log_data['user_agent'][log_data['user_agent']] = 1

        if log_data['page_visited'] in analyzed_log_data['pages_visited']:
            analyzed_log_data['pages_visited'][log_data['page_visited']] += 1
        else:
            analyzed_log_data['pages_visited'][log_data['page_visited']] = 1

    datetimes.sort()
    analyzed_log_data['earliest_date'] = datetimes[0].strftime('%d/%b/%Y:%H:%M:%S')
    analyzed_log_data['latest_date'] = datetimes[-1].strftime('%d/%b/%Y:%H:%M:%S')

    return(analyzed_log_data)

def output(**kwargs):
    """
    Creates output
    """
    analyzed_log_data = kwargs['data']
    hits = analyzed_log_data['hits']
    first_date = analyzed_log_data['earliest_date']
    last_date = analyzed_log_data['latest_date']
    output = f"Analysis of: {kwargs['file_name']}, from {first_date} to {last_date}:\n"
    output += f"Hits: {hits}\n"

    if 'visitor_ips' in analyzed_log_data:
        logger.debug(f"Visitor IPs in data: {analyzed_log_data['visitor_ips']}")
        output += f"IP addresses: \n"
        for data in analyzed_log_data['visitor_ips']:
            perc = analyzed_log_data['visitor_ips'][data]/analyzed_log_data['hits'] * 100
            if perc >= kwargs['percent']:
                output += f"{data}: {perc:.1f}%\n"

    ordered_status_data = sorted(analyzed_log_data['status'].items(), 
                                    key=lambda kv: kv[1], reverse=True)
    output += "Status Codes:\n"
    for (code, number) in ordered_status_data:
        perc = number/analyzed_log_data['hits'] * 100
        if perc >= kwargs['percent']:
            output += f"{code}: {perc:.1f}%\n"

    ordered_agent_data = sorted(analyzed_log_data['user_agent'].items(),
                                key=lambda kv: kv[1], reverse=True)
    output += f"Number of user agents: {len(ordered_agent_data)}\n"
    for (agent, number) in ordered_agent_data:
        perc = number/analyzed_log_data['hits'] * 100
        if perc >= kwargs['percent']:
            output += f"User agent {agent}: {perc:.1f}%\n"

    i = 0
    ordered_pages_visited = sorted(analyzed_log_data['pages_visited'].items(), key=lambda kv: kv[1], reverse=True)
    output += f"Number of pages visited: {len(ordered_pages_visited)}\n"
    output += f"Top {kwargs['num']} pages:\n"
    for (page, number) in ordered_pages_visited:
        perc = number/analyzed_log_data['hits'] * 100
        output += f"Page {page}: {number} {perc:.1f}%\n"
        i += 1
        if i > kwargs['num']:
            break

    return (output, first_date, last_date, hits)

def domain_log_reports(domain, report_type):
    """
    Reports of log reports
    """
    configs = get_configs()
    # get filtered list
    file_list = get_file_list(
        region=configs['region'],
        profile=configs['profile'],
        bucket=configs['log_storage_bucket'],
        domain=domain,
        filter='Output'
    )

    if not file_list:
        return False

    # Sort by date
    sorted_list = sorted(file_list, key=lambda i: i['date'], reverse=True)

    if report_type == 'latest':
        output_contents = get_output_contents(
            bucket=configs['log_storage_bucket'],
            profile=configs['profile'],
            region=configs['region'],
            output_file=sorted_list[0]['file_name'],
            local_tmp=configs['local_tmp'])
        return output_contents

def domain_log_list(domain, num):
    """
    List of domain logs
    """
    configs = get_configs()
    # get filtered list
    file_list = get_file_list(
        region=configs['region'],
        profile=configs['profile'],
        bucket=configs['log_storage_bucket'],
        domain=domain,
        filter='Raw'
    )

    if not file_list:
        return False

    sorted_list = sorted(file_list, key=lambda i: i['date'], reverse=True)

    return sorted_list[0:num]

def get_output_contents(**kwargs):
    """
    Gets the contents of specific output file
    """
    s3simple = S3Simple(region_name=kwargs['region'],
                        bucket_name=kwargs['bucket'],
                        profile=kwargs['profile'])
    local_file_name = kwargs['local_tmp'] + '/' + kwargs['output_file']
    s3simple.download_file(file_name=kwargs['output_file'], output_file=local_file_name)

    with open(local_file_name) as f:
        output = f.read()

    return output

def get_file_list(**kwargs):
    """
    Get the right list of files, keyed by date
    """
    s3simple = S3Simple(region_name=kwargs['region'],
                        bucket_name=kwargs['bucket'],
                        profile=kwargs['profile'])
    file_list = s3simple.s3_bucket_contents()
    filtered_list = []
    for single_file in file_list:
        if (kwargs['filter'] in single_file) and (kwargs['domain'] in single_file):
            date_search = '[0-9]{2}[-][a-zA-Z]{3}-20[0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{2}'
            match = re.search(date_search, single_file)
            date = datetime.datetime.strptime(match.group(0),'%d-%b-%Y:%H:%M:%S')
            filtered_list.append({'date': date, 'file_name': single_file})

    return filtered_list
    
def get_domain_data(domain):
    """
    Get domain data
    """
    load_dotenv()

    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()

    domains = db.Table('domains', metadata, autoload=True, autoload_with=engine)

    ## Get domain id
    query = db.select([domains])
    result = connection.execute(query).fetchall()
    
    domain_data = {
        'id': False
    }
    for entry in result:
        d_id, domain_fetched, ext_ignore, paths_ignore = entry
        if domain_fetched in domain:
            domain_data['id'] = d_id
            domain_data['ext_ignore'] = ext_ignore
            domain_data['paths_ignore'] = paths_ignore
    
    if not domain_data['id']: # we've not seen it before, add it
        insert = domains.insert().values(domain=domain)
        result = connection.execute(insert)
        domain_data['id'] = result.inserted_primary_key[0]

    return domain_data

def report_save(**kwargs):
    """
    Saving report to database
    """
    domain_data = get_domain_data(kwargs['domain'])
    domain_id = domain_data['id']
    load_dotenv()

    engine = db.create_engine(os.environ['DATABASE_URL'])
    connection = engine.connect()
    metadata = db.MetaData()
    log_reports = db.Table('log_reports', metadata, autoload=True, autoload_with=engine)

    # Save report
    report_data = {
            'date_of_report': kwargs['datetime'],
            'domain_id': domain_id,
            'report': kwargs['report_text'],
            'hits':kwargs['hits'],
            'first_date_of_log':kwargs['first_date_of_log'],
            'last_date_of_log':kwargs['last_date_of_log'],
            'log_type':kwargs['log_type']
        }
    insert = log_reports.insert().values(**report_data)
    result = connection.execute(insert)
    report_id = result.inserted_primary_key[0]

    logger.debug(f"Report ID: {report_id}")

    return
