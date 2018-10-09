import boto3
import botocore
import sys

globalVars = {}
globalVars['REGION_NAME']           = "eu-west-2"
globalVars['AZ1']                   = "eu-west-2a"
globalVars['AZ2']                   = "eu-west-2b"
globalVars['CIDRange']              = "176.32.125.0/25"
globalVars['EC2-AMI-ID']            = "ami-0b0a60c0a2bd40612"
globalVars['EC2-InstanceType']      = "t2.micro"
globalVars['EC2-KeyName']           = "London_test1-key"
globalVars['tagName']               = "London_test"

# Delete the instances
ids=[]
for i in instanceLst:
    ids.append(i.id)

ec2.instances.filter(InstanceIds=ids).terminate()

# Wait for the instance to be terminated
# Boto waiters might be best, for this demo, i will will "sleep"
from time import sleep
sleep(120)

ec2Client.delete_key_pair( KeyName = globalVars['EC2-KeyName'] )

# Delete Routes & Routing Table
for assn in rtbAssn:
    ec2Client.disassociate_route_table( AssociationId = assn.id )

routeTable.delete()

# Delete Subnets
az1_pvtsubnet.delete()
az1_pubsubnet.delete()
az1_sparesubnet.delete()

# Detach & Delete internet Gateway
ec2Client.detach_internet_gateway( InternetGatewayId = intGateway.id , VpcId = vpc.id )
intGateway.delete()

# Delete Security Groups
pubSecGrp.delete()
pvtSecGrp.delete()

vpc.delete()