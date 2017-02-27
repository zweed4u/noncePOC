# make use of config - ssh credentials and path to blob and if nonceEnabler is needed
# dependency check/install tihmstar stuff 
import os, sys, time, datetime, requests, paramiko, ConfigParser
from scp import SCPClient

# Get the project directory to avoid using relative paths
rootDirectory = os.getcwd()

# Parse configuration file
c = ConfigParser.ConfigParser()
configFilePath = os.path.join(rootDirectory, 'config.cfg')
c.read(configFilePath)

class Config:
    # Pull user info 
    binNeeded = c.get('nonce','binNeeded')
    runEnabler = c.get('nonce','runEnabler')
    iosIp = c.get('ssh', 'iosIp')
    iosSshPass = c.get('ssh','iosPassword')
    localPass = c.get('ssh','localPassword')
    poc = c.get('POC', 'showPOC')
    blobPath = c.get('shsh2', 'pathToBlob')

class SSH:
	ssh=paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	def __init__(self, address, port, user, passwd):
		self.address = address
		self.port = port
		self.user = user
		self.passwd = passwd
	def connect(self):
		SSH.ssh.connect(self.address,self.port,self.user,self.passwd)

user_config = Config()

for line in open(blobPath,'r'):
	if '<string>0x' in line: #ensure that each generator follows the same pattern (hex 0x and xml-esque <>__<>)
		generator = line.split('>')[1].split('<')[0]

if user_config.binNeeded.lower() == 'true':
	fetchBinSession=requests.session()
	binUrl='https://people.rit.edu/zdw7287/files/nonceEnabler/nonceEnabler'

	print 'Downloading nonceEnabler binary...'
		r=fetchBinSession.get(binUrl)
		local_filename = binUrl.split('/')[-1]
		with open(local_filename, 'wb') as f:
			for chunk in r.iter_content(chunk_size=1024): 
				if chunk: # filter out keep-alive new chunks
					f.write(chunk)

		print 'SSHing into device using config vals...'
		ios_ssh = SSH(user_config.iosIp, 22, 'root', user_config.iosSshPass)
		ios_ssh.connect()
		scp = SCPClient(ios_ssh.ssh.get_transport())

		print 'SCPing downloaded binary to device...'
		scp.put(os.path.join(rootDirectory, local_filename))

		print 'Setting nonceEnabler permissions...'
		stdin, stdout, stderr = ios_ssh.ssh.exec_command('chmod +x '+local_filename)
		for i in stdout.readlines():
			print i

		print 'Running nonceEnabler...'
		stdin, stdout, stderr = ios_ssh.ssh.exec_command('./'+local_filename)
		for i in stdout.readlines():
			print i

		print 'Setting nvram generator variable for boot-nonce...'
		stdin, stdout, stderr = ios_ssh.ssh.exec_command('nvram com.apple.System.boot-nonce='+generator)
		for i in stdout.readlines():
			print i

		print 'Ensuring nvram variable was written...'
		stdin, stdout, stderr = ios_ssh.ssh.exec_command('nvram -p') #maybe grep this with the generator or com.apple.System.boot-nonce
		for i in stdout.readlines():
			print i # assert that the variable written matches the generator

if user_config.runEnabler.lower() == 'true':
	print 'SSHing into device using config vals...'
	ios_ssh = SSH(user_config.iosIp, 22, 'root', user_config.iosSshPass)
	ios_ssh.connect()

	print 'Setting nonceEnabler permissions...'
		stdin, stdout, stderr = ios_ssh.ssh.exec_command('chmod +x '+local_filename)
		for i in stdout.readlines():
			print i

	print 'Running nonceEnabler...'
	stdin, stdout, stderr = ios_ssh.ssh.exec_command('./'+local_filename)
	for i in stdout.readlines():
		print i

	print 'Setting nvram generator variable for boot-nonce...'
	stdin, stdout, stderr = ios_ssh.ssh.exec_command('nvram com.apple.System.boot-nonce='+generator)
	for i in stdout.readlines():
		print i

	print 'Ensuring nvram variable was written...'
	stdin, stdout, stderr = ios_ssh.ssh.exec_command('nvram -p') #maybe grep this with the generator or com.apple.System.boot-nonce
	for i in stdout.readlines():
		print i # assert that the variable written matches the generator


#need to terminate ios ssh session
if user_config.poc.lower() == 'true':
	local_ssh = SSH('127.0.0.1', 22, os.getlogin(), user_config.localPass)
	local_ssh.connect()
	bnchNonce = str(local_ssh.ssh.exec_command('img4tool -s '+blobPath+' | grep BNCH')).split('BNCH: ')[2] #Format - BNCH: BNCH: (NONCE HERE)
	print 'Connect your idevice in its jailbroken state - nonce should already have been set by enabler'
	deviceNonce = str(local_ssh.ssh.exec_command('sudo noncestatistics -t 1 test.txt | grep ApNonce')).split('=')[1] #log in as root or password will be needed
	assert deviceNonce == bnchNonce, "Error Message: Nonces do not match!"

print 'Ensure that you are currently in a jailbroken state and that you have the blobs.'
print 'Visit jbme.qwertyoruiop.com on your device for tfp0'

# fetch path to blob from config and parse and store generator
# fetch ssh credentials from config
# wget nonceEnabler and scp over it to phone fetch path to downloaded file 
# ssh in and ./nonceEnabler - maybe handle with the last output of the command
# set nvram var with com.apple.System.boot-nonce=(FETCHED AND PARSED GENERATOR FROM BEFORE)

# POC - version - extend to desktop - sudo noncestatistics -t 1 test.txt | grep ApNonce 
# assert that the nonce is equal to img4tool -s (FETCHED PATH TO BLOB)) | grep BNCH