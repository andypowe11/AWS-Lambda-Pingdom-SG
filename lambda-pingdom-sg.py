'''
Update a set of security groups in order to whitelist all the Pingdom probe IP
addresses, allowing inbound traffic on ports 80 and 443. This typically requires
3 security groups (for ~70 IP addresses, assuming the default limit of 50
inbound rules per SG and 2 ingress ports per IP address.

Heavily based on https://blogs.aws.amazon.com/security/post/Tx1LPI2H6Q6S5KC/How-to-Automatically-Update-Your-Security-Groups-for-Amazon-CloudFront-and-AWS-W

Andy Powell
22/05/2016
'''

import boto3
import urllib2
 
# URL of the list of Pingdom probe IP addresses to be whitelisted
SOURCE = "https://my.pingdom.com/probes/ipv4"
# Ports that need inbound permissions from the Pingdom probes
INGRESS_PORTS = [ 80, 443 ]
# Tags which identify the security groups you want to update
SECURITY_GROUP_TAGS = { 'Name': 'pingdom*', 'AutoUpdate': 'true' }
# Limit on inbound rules per Security Group (default: 50)
RULES_PER_SG = 50
# Region to search for Security Groups 
AWS_REGION = "us-east-1"
 
def lambda_handler(event, context):
    # Load the IP addresses from the SOURCE URL
    addresses = get_ip_addresses(SOURCE)
    print('Downloaded ' + str(len(addresses)) + ' IP addresses from ' + SOURCE + 'to whitelist')
    
    # Find available security groups based on the SECURITY_GROUP_TAGS
    client = boto3.client('ec2', region_name=AWS_REGION)
    groups = get_security_groups_for_update(client)
    print ('Found ' + str(len(groups)) + ' security groups to use')
    
    # update the security groups
    result = update_security_groups(client, groups, addresses)
    
    return result
    
def get_ip_addresses(url):
    response = urllib2.urlopen(url)
    ip_list = response.read()
    
    return [ip.strip() for ip in ip_list.splitlines()]

def get_security_groups_for_update(client):
    filters = list();
    for key, value in SECURITY_GROUP_TAGS.iteritems():
        filters.extend(
            [
                { 'Name': "tag-key", 'Values': [ key ] },
                { 'Name': "tag-value", 'Values': [ value ] }
            ]
        )
    response = client.describe_security_groups(Filters=filters)
    
    return response['SecurityGroups']
    
def update_security_groups(client, groups, addresses):
    result = list()
    groupsupdated = 0
    groupindex = 0
    ipaddresses = 0
    for group in groups:
        start = groupindex * RULES_PER_SG / 2
        end = start + RULES_PER_SG / 2
        addrsubset = addresses[start:end]
        print('Adding ' + str(len(addrsubset)) + ' IP addresses to ' + group['GroupId'])
        clear_security_group(client, group)
        if update_security_group(client, group, addrsubset):
            groupindex += 1
            groupsupdated += 1
            result.append('Updated ' + group['GroupId'])
    result.append('Updated ' + str(groupsupdated) + ' of ' + str(len(groups)) + ' security groups')
    
    return result

def clear_security_group(client, group):
    removed = 0
    if len(group['IpPermissions']) > 0:
        for permission in group['IpPermissions']:
            to_revoke = list()
            for range in permission['IpRanges']:
                cidr = range['CidrIp']
                to_revoke.append(range)
            removed += revoke_permissions(client, group, permission, to_revoke)
        print (group['GroupId'] + ": Revoked " + str(removed) + ' rules')
        
    return(1)

def update_security_group(client, group, addresses):
    added = 0
    for port in INGRESS_PORTS:
        to_add = list()
        for address in addresses:
            range = address + "/32"
            to_add.append({ 'CidrIp': range })
        permission = { 'ToPort': port, 'FromPort': port, 'IpProtocol': 'tcp'}
        added += add_permissions(client, group, permission, to_add)
    print(group['GroupId'] + ": Added " + str(added) + ' rules')
    
    return(added > 0)
 
def revoke_permissions(client, group, permission, to_revoke):
    if len(to_revoke) > 0:
        revoke_params = {
            'ToPort': permission['ToPort'],
            'FromPort': permission['FromPort'],
            'IpRanges': to_revoke,
            'IpProtocol': permission['IpProtocol']
        }
        client.revoke_security_group_ingress(GroupId=group['GroupId'], IpPermissions=[revoke_params])
        
    return len(to_revoke)

def add_permissions(client, group, permission, to_add):
    if len(to_add) > 0:
        add_params = {
            'ToPort': permission['ToPort'],
            'FromPort': permission['FromPort'],
            'IpRanges': to_add,
            'IpProtocol': permission['IpProtocol']
        }
        client.authorize_security_group_ingress(GroupId=group['GroupId'], IpPermissions=[add_params])
        
    return len(to_add)
