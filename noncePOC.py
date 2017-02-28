# make use of config - ssh credentials and path to blob and if nonceEnabler is needed
# dependency check/install tihmstar stuff 
import os, sys, time, datetime, requests, paramiko, ConfigParser
from scp import SCPClient

print 'Please ensure that your iDevice is in a jailbroken state and has tfp0 support.'
print '***If you are unsure - please visit jbme.qwertyoruiop.com on your device before proceeding***'
raw_input('')

# Get the project directory to avoid using relative paths
rootDirectory = os.getcwd()

# Parse configuration file
c = ConfigParser.ConfigParser()
configFilePath = os.path.join(rootDirectory, 'config.cfg')
c.read(configFilePath)

class Config:
    # Pull user info 
    blobPath = c.get('shsh2', 'pathToBlob')
    binNeeded = c.get('nonce','binNeeded')
    runEnabler = c.get('nonce','runEnabler')
    iosIp = c.get('ssh', 'iosIp')
    iosSshPass = c.get('ssh','iosPassword')
    localPass = c.get('ssh','localPassword')
    poc = c.get('POC', 'showPOC')

class SSH:
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	def __init__(self, address, port, user, passwd):
		self.address = address
		self.port = port
		self.user = user
		self.passwd = passwd
	def connect(self):
		SSH.ssh.connect(self.address, self.port, self.user, self.passwd)

class color:
		PURPLE = '\033[95m'
		CYAN = '\033[96m'
		DARKCYAN = '\033[36m'
		BLUE = '\033[94m'
		GREEN = '\033[92m'
		YELLOW = '\033[93m'
		RED = '\033[91m'
		BOLD = '\033[1m'
		UNDERLINE = '\033[4m'
		END = '\033[0m'

print str(datetime.datetime.now())+' :: Loading config information...'
user_config = Config()

if user_config.binNeeded.lower() == 'false':
	print 'Ensure that the binary is titled "nonceEnabler" and in /var/root'
	raw_input('')

ios_ssh = SSH(user_config.iosIp, 22, 'root', user_config.iosSshPass)
local_ssh = SSH('127.0.0.1', 22, os.getlogin(), user_config.localPass)

def nvramWrite(iOSSession, generator, binaryFileName=None):
	if binaryFileName == None:
		binaryFileName = 'nonceEnabler'
	print str(datetime.datetime.now())+' :: Setting nonceEnabler permissions...'
	stdin, stdout, stderr = iOSSession.ssh.exec_command('chmod +x '+binaryFileName)

	print str(datetime.datetime.now())+' :: Running nonceEnabler...'
	stdin, stdout, stderr = iOSSession.ssh.exec_command('./'+binaryFileName)
	print color.CYAN+str(stdout.read())+color.END

	print str(datetime.datetime.now())+' :: Setting nvram generator variable for boot-nonce...'
	iOSSession.ssh.exec_command('nvram com.apple.System.boot-nonce='+generator)

	print str(datetime.datetime.now())+' :: Ensuring nvram variable was written...'
	stdin, stdout, stderr = iOSSession.ssh.exec_command('nvram -p') #maybe grep this with the generator or com.apple.System.boot-nonce
	nvramOutput=str(stdout.read())
	print color.CYAN+nvramOutput+color.END # assert that the variable written matches the generator
	nvramVar = nvramOutput.split('com.apple.System.boot-nonce')[1].split('\t')[1].split('\n')[0]
	assert nvramVar == generator, "Error Message: Expected ["+generator+"] but ["+nvramVar+"] was written to nvram."
	print str(datetime.datetime.now())+' :: nvram assertion passed with '+nvramVar+' set as generator.'

for line in open(user_config.blobPath, 'r'):
	if '<string>0x' in line: # ensure that each generator follows the same pattern (hex 0x and xml-esque <>__<>)
		generator = line.split('>')[1].split('<')[0]

if user_config.binNeeded.lower() == 'true':
	fetchBinSession = requests.session()
	binUrl = 'https://people.rit.edu/zdw7287/files/nonceEnabler/nonceEnabler'
	print str(datetime.datetime.now())+' :: Downloading nonceEnabler binary...'
	r = fetchBinSession.get(binUrl)
	local_filename = binUrl.split('/')[-1]
	with open(local_filename, 'wb') as f:
		for chunk in r.iter_content(chunk_size=1024): 
			if chunk: # filter out keep-alive new chunks
				f.write(chunk)

	print str(datetime.datetime.now())+' :: SSHing into device using config vals...'
	ios_ssh.connect()
	print str(datetime.datetime.now())+' :: Connected'

	print str(datetime.datetime.now())+' :: SCPing downloaded binary to device...'
	scp = SCPClient(local_ssh.ssh.get_transport())
	scp.put(os.path.join(rootDirectory, local_filename))

	nvramWrite(iOSSession=ios_ssh, generator=generator, binaryFileName=local_filename)

if user_config.runEnabler.lower() == 'true':
	print str(datetime.datetime.now())+' :: SSHing into device using config vals...'
	ios_ssh.connect()
	print str(datetime.datetime.now())+' :: Connected'

	nvramWrite(iOSSession=ios_ssh, generator=generator)

ios_ssh.ssh.close()

if user_config.poc.lower() == 'true':
	print str(datetime.datetime.now())+' :: Making ssh loopback connection for local commands..'
	local_ssh.connect()
	print str(datetime.datetime.now())+' :: Connected'
	print str(datetime.datetime.now())+' :: Checking saved shsh2 blobs nonce with img4tool...'
	stdin, stdout, stderr = local_ssh.ssh.exec_command('img4tool -s '+user_config.blobPath)
	img4toolOuput=str(stdout.read())
	print color.CYAN+img4toolOuput+color.END 
	bnchNonce=img4toolOuput.split('BNCH: ')[2].split('\n')[0]

	print str(datetime.datetime.now())+' :: Extracted nonce from blob: '+bnchNonce
	print str(datetime.datetime.now())+' :: Connect your idevice in its jailbroken state - nonce should already have been set by enabler'
	print str(datetime.datetime.now())+' :: Press Enter when device is connected.'
	raw_input('')

	stdin, stdout, stderr = local_ssh.ssh.exec_command('sudo -S noncestatistics -t 1 test.txt',get_pty=True) #maybe grep this with the generator or com.apple.System.boot-nonce
	stdin.write( user_config.localPass+"\n")
	stdin.flush()
	noncestatisticsOutput=str(stdout.read()).split('\n')[3:]
	for line in noncestatisticsOutput:
		if 'ApNonce' in line:
			deviceNonce=line.split('ApNonce=')[1]
		print color.CYAN+line+color.END 

	print str(datetime.datetime.now())+' :: Nonce pulled from device: '+ deviceNonce 
	print str(datetime.datetime.now())+' :: Nonce pulled from shsh2: '+ bnchNonce 
	assert str(bnchNonce) in str(deviceNonce), "Error Message: Nonces do not match! Nonce from device is "+deviceNonce+' and nonce of blob used is '+bnchNonce
	print str(datetime.datetime.now())+' :: nonce assertion passed with '+deviceNonce
