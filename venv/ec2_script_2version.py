ec2         = boto3.resource ( 'ec2', region_name = globalVars['eu-west-2'] )
ec2Client   = boto3.client   ( 'ec2', region_name = globalVars['eu-west-2'] )
vpc         = ec2.create_vpc ( CidrBlock = globalVars['CIDRange']  )


# AZ1 Subnets
az1_pvtsubnet   = vpc.create_subnet( CidrBlock = '10.242.0.0/25'   , AvailabilityZone = globalVars['AZ1'] )
az1_pubsubnet   = vpc.create_subnet( CidrBlock = '10.242.0.128/26' , AvailabilityZone = globalVars['AZ1'] )
az1_sparesubnet = vpc.create_subnet( CidrBlock = '10.242.0.192/26' , AvailabilityZone = globalVars['AZ1'] )


# Enable DNS Hostnames in the VPC
vpc.modify_attribute( EnableDnsSupport   = { 'Value': True } )
vpc.modify_attribute( EnableDnsHostnames = { 'Value': True } )

# Create the Internet Gatway & Attach to the VPC
intGateway  = ec2.create_internet_gateway()
intGateway.attach_to_vpc( VpcId = vpc.id )

# Create another route table for Public & Private traffic
routeTable = ec2.create_route_table( VpcId = vpc.id )

rtbAssn=[]
rtbAssn.append(routeTable.associate_with_subnet( SubnetId = az1_pubsubnet.id ))
rtbAssn.append(routeTable.associate_with_subnet( SubnetId = az1_pvtsubnet.id ))

# Create a route for internet traffic to flow out
intRoute = ec2Client.create_route( RouteTableId = routeTable.id,
                                   DestinationCidrBlock = '0.0.0.0/0',
                                   GatewayId = intGateway.id
                                   )

# Tag the resources
tag = vpc.create_tags               ( Tags=[{'Key': globalVars['tagName'] , 'Value':'vpc'}] )
tag = az1_pvtsubnet.create_tags     ( Tags=[{'Key': globalVars['tagName'] , 'Value':'az1-private-subnet'}] )
tag = az1_pubsubnet.create_tags     ( Tags=[{'Key': globalVars['tagName'] , 'Value':'az1-public-subnet'}] )
tag = az1_sparesubnet.create_tags   ( Tags=[{'Key': globalVars['tagName'] , 'Value':'az1-spare-subnet'}] )
tag = intGateway.create_tags        ( Tags=[{'Key': globalVars['tagName'] , 'Value':'igw'}] )
tag = routeTable.create_tags        ( Tags=[{'Key': globalVars['tagName'] , 'Value':'rtb'}] )

# Let create the Public & Private Security Groups
pubSecGrp = ec2.create_security_group( DryRun = False,
                              GroupName='pubSecGrp',
                              Description='Public_Security_Group',
                              VpcId= vpc.id
                            )

pvtSecGrp = ec2.create_security_group( DryRun = False,
                              GroupName='pvtSecGrp',
                              Description='Private_Security_Group',
                              VpcId= vpc.id
                            )

pubSecGrp.create_tags(Tags=[{'Key': globalVars['tagName'] ,'Value':'public-security-group'}])
pvtSecGrp.create_tags(Tags=[{'Key': globalVars['tagName'] ,'Value':'private-security-group'}])

# Add a rule that allows inbound SSH, HTTP, HTTPS traffic ( from any source )
ec2Client.authorize_security_group_ingress( GroupId  = pubSecGrp.id ,
                                        IpProtocol= 'tcp',
                                        FromPort=80,
                                        ToPort=80,
                                        CidrIp='0.0.0.0/0'
                                        )
ec2Client.authorize_security_group_ingress( GroupId  = pubSecGrp.id ,
                                        IpProtocol= 'tcp',
                                        FromPort=443,
                                        ToPort=443,
                                        CidrIp='0.0.0.0/0'
                                        )
ec2Client.authorize_security_group_ingress( GroupId  = pubSecGrp.id ,
                                        IpProtocol= 'tcp',
                                        FromPort=22,
                                        ToPort=22,
                                        CidrIp='0.0.0.0/0'
                                        )
### Check if key is already present
customEC2Keys = ec2Client.describe_key_pairs()['KeyPairs']
if not next((key for key in customEC2Keys if key["KeyName"] == globalVars['EC2-KeyName'] ),False):
    ec2_key_pair = ec2.create_key_pair( KeyName = globalVars['EC2-KeyName'] )
    print ("New Private Key created,Save the below key-material\n\n")
    print ( ec2_key_pair.key_material )
##### **DeviceIndex**:The network interface's position in the attachment order.
##### For example, the first attached network interface has a DeviceIndex of 0
instanceLst = ec2.create_instances(ImageId = globalVars['ami-0bdf93799014acdc4],
                                   MinCount=1,
                                   MaxCount=1,
                                   KeyName=globalVars['EC2-KeyName'] ,
                                   #UserData = userDataCode,
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
