# SSH connection to the instance
import paramiko

my_key = paramiko.RSAKey.from_private_key_file(Ireland_key.pem)
 client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname=instance_ip, username='ubuntu', pkey=my_key)
stdin, stdout, stderr = ssh.exec_command('uptime')
stdout.readlines()