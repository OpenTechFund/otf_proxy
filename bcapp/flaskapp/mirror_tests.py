import json
import re
import base64
from github import Github
import requests
import urllib3
from requests_html import HTMLSession
from proxy_utilities import get_configs
from repo_utilities import check, convert_domain

def test_domain(domain, proxy, mode):
    """
    Get response code from domain
    :param domain
    :returns status code (int)
    """
    https_domain = 'https://' + domain
    http_domain = 'http://' + domain
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if mode == 'console':
        print(f"Testing {domain}...")
    if proxy:
        print(f"Using proxy: {proxy}...")
        if 'https' in proxy:
            request_proxy = { 'https' : proxy}
        else:
            request_proxy = { 'http': proxy}
    try:
        if proxy:
            response = requests.get(https_domain, proxies=request_proxy)
        else:
            response = requests.get(https_domain)
        response_return = response.status_code
        response_url = response.url
    except Exception as e:
        try:
            if proxy:
                response = requests.get(http_domain, proxies=request_proxy)
            else:
                response = requests.get(http_domain)
            response_return = response.status_code
            response_url = response.url
        except Exception as e:
            return 500, ""
    
    return response_return, response_url

def test_onion(onion, mode):
    session = requests.session()
    session.proxies = {
        'http': 'socks5h://localhost:9050',
        'https': 'socks5h://localhost:9050'
        }
    full_onion = 'https://' + onion
    if mode == 'console':
        print(f"Testing {onion}...")
    try:
        r = session.get(full_onion, verify=False)
    except:
        print("TOR not properly configured!")
        return 500, full_onion
        
    return r.status_code, full_onion

def mirror_detail(**kwargs):
    """
    List and test mirrors for a domain
    :arg kwargs:
    :kwarg domain
    :kwarg proxy
    :kwarg mode
    :returns: json with data
    """
    output = {}
    domain = kwargs['domain']
    if kwargs['mode'] == 'console':
        print(f"Listing and Testing {domain}...")
    output['domain'] = domain
    domain_data = check(domain)
    exists = domain_data['exists']
    current_mirrors = domain_data['available_mirrors']
    current_onions = domain_data['available_onions'] 
    current_ipfs_nodes = domain_data['available_ipfs_nodes']
    current_alternatives = domain_data['available_alternatives']

    if not exists:
        if kwargs['mode'] == 'console':
            print(f"{domain} doesn't exist in the mirror list.")
        return False
    if kwargs['mode'] == 'console':  
        print(f"Mirror list: {current_mirrors} Onions: {current_onions}, IPFS Nodes: {current_ipfs_nodes}, Alternatives: {current_alternatives}")

    mresp, murl = test_domain(domain, kwargs['proxy'], kwargs['mode'])
    if kwargs['mode'] == 'console':
        print(f"Response code on domain: {mresp}, url: {murl}")
    output[domain] = mresp

    if not current_alternatives:
        output['current_mirrors'] = current_mirrors
        output['current_onions'] = current_onions
        output['current_ipfs_nodes'] = current_ipfs_nodes
        
        if current_mirrors:
            for mirror in current_mirrors:
                mresp, murl = test_domain(mirror, kwargs['proxy'], kwargs['mode'])
                if kwargs['mode'] == 'console':
                    print(f"Response code on mirror: {mresp}, url: {murl}")
                output[mirror] = mresp
        if current_onions:
            for onion in current_onions:
                mresp, murl = test_onion(onion, kwargs['mode'])
                if kwargs['mode'] == 'console':
                    print(f"Onion {onion}... Response code: {mresp} ... URL: {murl}")
                output[onion] = mresp

        if current_ipfs_nodes:
            ## Testing here
            pass
        if kwargs['mode'] == 'console':
            convert = input("This entry is in version 1 mode. Convert to Version 2 alternatives (Y/n)?")
            if convert.lower() != 'n':
                delete = input("Delete deprecated keys like 'available_mirrors' (y/N)?")
                convert_domain(domain, delete)

    else: # format is alternatives
        output['current_alternatives'] = current_alternatives
        for alternative in current_alternatives:
            if alternative['proto'] == 'http' or alternative['proto'] == 'https':
                mresp, murl = test_domain(alternative['url'], kwargs['proxy'], kwargs['mode'])
                if kwargs['mode'] == 'console':
                    print(f"Response code on mirror: {mresp}, url: {murl}")
                output[alternative['url']] = mresp
            elif alternative['proto'] == 'tor':
                mresp, murl = test_onion(alternative['url'], kwargs['mode'])
                if kwargs['mode'] == 'console':
                    print(f"Onion {alternative['url']}... Response code: {mresp} ... URL: {murl}")
                output[alternative['url']] = mresp
            elif alternative['proto'] == 'ipfs':
                pass
            else:
                pass

        
    return output
