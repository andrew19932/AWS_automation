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

userDataCode = """
#!/bin/bash
set -e -x

# Setting up the HTTP server 
yum install -y httpd php php-mysql mysql
systemctl start httpd
systemctl enable httpd
groupadd www
usermod -a -G www ec2-user

# SE Linux permissive
# needed to make wp connect to DB over newtork
setsebool -P httpd_can_network_connect=1
setsebool httpd_can_network_connect_db on

systemctl restart httpd
#show cpu, free memory
echo CPU: `top -b -n1 | grep "Cpu(s)" | awk '{print $2 + $4}'` 
FREE_DATA=`free -m | grep Mem` 
CURRENT=`echo $FREE_DATA | cut -f3 -d' '`
TOTAL=`echo $FREE_DATA | cut -f2 -d' '`
echo RAM: $(echo "scale = 2; $CURRENT/$TOTAL*100" | bc)
echo HDD: `df -lh | awk '{if ($6 == "/") { print $5 }}' | head -1 | cut -d'%' -f1`
"""

# create VPC, subnet, gateway
ec2 = boto3.resource( 'ec2', region_name = globalVars['REGION_NAME'] )
ec2Client   = boto3.client   ( 'ec2', region_name = globalVars['REGION_NAME'] )
vpc = ec2.create_vpc( CidrBlock = globalVars['CIDRange'] )

az1_pubsubnet   = vpc.create_subnet( CidrBlock = globalVars['CIDRange'] , AvailabilityZone = globalVars['AZ1'] )
intGateway  = ec2.create_internet_gateway()
tag = vpc.create_tags( Tags=[ { 'Key': 'Name', 'Value':'vpc_new' } ] )
print(vpc.id)

# Enable DNS Hostnames in the VPC
vpc.modify_attribute( EnableDnsSupport   = { 'Value': True } )
vpc.modify_attribute( EnableDnsHostnames = { 'Value': True } )

# Create the Internet Gatway & Attach to the VPC
intGateway  = ec2.create_internet_gateway()
intGateway.attach_to_vpc( VpcId = vpc.id )

# Create another route table for Public & Private traffic
routeTable = ec2.create_route_table( VpcId = vpc.id )

rtbAssn=[]
rtbAssn.append( routeTable.associate_with_subnet( SubnetId = az1_pubsubnet.id ) )

### Check if key is already present
customEC2Keys = ec2Client.describe_key_pairs()['KeyPairs']
if not next((key for key in customEC2Keys if key["KeyName"] == globalVars['EC2-KeyName'] ),False):
    ec2_key_pair = ec2.create_key_pair( KeyName = globalVars['EC2-KeyName'] )
    print ("New Private Key created,Save the below key-material\n\n")
    print ( ec2_key_pair.key_material )

# Create sec group
# Let create the Public & Private Security Groups
pubSecGrp = ec2.create_security_group( DryRun = False,
                              GroupName='pubSecGrp',
                              Description='Public_Security_Group',
                              VpcId= vpc.id
                            )
pubSecGrp.create_tags( Tags = [ { 'Key': globalVars['tagName'] ,'Value':'public-security-group' } ] )

# Add a rule that allows inbound SSH, HTTP, HTTPS traffic ( from any source )
ec2Client.authorize_security_group_ingress( GroupId  = pubSecGrp.id ,
                                        IpProtocol= 'tcp',
                                        FromPort=80,
                                        ToPort=80,
                                        CidrIp='0.0.0.0/0'
                                        )
ec2Client.authorize_security_group_ingress( GroupId  = pubSecGrp.id ,
                                        IpProtocol= 'tcp',
                                        FromPort=22,
                                        ToPort=22,
                                        CidrIp='0.0.0.0/0'
                                        )
#### creating a new instance ####
instanceLst = ec2.create_instances(ImageId = globalVars['EC2-AMI-ID'],
                                   MinCount=1,
                                   MaxCount=1,
                                   KeyName=globalVars['EC2-KeyName'] ,
                                   UserData = userDataCode,
                                   InstanceType = globalVars['EC2-InstanceType'],
                                   NetworkInterfaces=[
                                                        {
                                                            'SubnetId': az1_pubsubnet.id,
                                                            'Groups': [ pubSecGrp.id ],
                                                            'DeviceIndex':0,
                                                            'DeleteOnTermination': True,
                                                            'AssociatePublicIpAddress': True,
                                                        }
                                                    ]
                                )
#### Create a volume ####
# create_volume(size, zone, snapshot=None, volume_type=None, iops=None)
# conn = boto.connect_ec2( 'Key': globalVars['EC2-KeyName'] , aws_secret_access_key = 'I7e8O8FZ2cn2K3+FCuXI4yoU1uoxxVuItp1KslW1' )
vol = ec2.create_volume( Size = 1, AvailabilityZone = "globalVars['REGION_NAME']", VolumeType = "standart" )
print 'Volume Id: ', vol.id

#### Attach the volume ####
response = volume.attach_to_instance( InstanceId=instance[0].instance_id, Device=’sdb’)
waiter = ec2_client.get_waiter(‘volume_in_use’)

waiter.wait(VolumeIds=[volume.volume_id])
# We can check if the volume is now ready and available:
curr_vol = conn.get_all_volumes([vol.id])[0]
while curr_vol.status == 'creating':
      curr_vol = conn.get_all_volumes([vol.id])[0]
      print 'Current Volume Status: ', curr_vol.status
      time.sleep(2)
print 'Current Volume Zone: ', curr_vol.zone
#### Attach a volume ####
result = conn.attach_volume (vol.id, instance.id, "/dev/sdf")
print 'Attach Volume Result: ', result


