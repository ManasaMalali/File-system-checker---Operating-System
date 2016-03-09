#File checker system - csefsck
# This file checker system runs through the file system, and checks for errors
import json
import sys
import mmap
import time
import subprocess
import os
import re
BLOCKSIZE= 4096
#specify the pathname of the data here
PATHNAME = '/home/manasa/FS/FS/'
superblock = 'fusedata.0'
print ('Running the cse file system checker-csefsck')
filedirectorylist = [] 

# [1]check if the device Id is 20, if not then exit:
with open(superblock, 'r') as f:
	objdata = json.load(f)
	list1 = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
	if list1.find('devId') != -1:
		dId = objdata['devId']
		if dId == 20:
			print ('This is the correct file system, you can proceed further.')
		else:
			print ('Error!!! This is not the correct file system, please check again.')
			sys.exit()

# [2]check if all the times are in the past
def checks(obj,filename):		
	if 'atime' in obj and 'ctime' in obj and 'mtime' in obj:
		CURRENTTIME = int(time.time())
		accesstime = obj['atime']
    		if accesstime <= CURRENTTIME:
			print "The Access time is in past and is correct :" + str(accesstime)
						
		else:
			print "The Access time is not in past, Setting it to the current time as it is in future. "
			obj['atime'] = CURRENTTIME
			with open(filename, 'r+') as f:
	 			f.seek(0)
	 			json.dump(obj, f)
		creationtime = obj['ctime']	
		if creationtime <= CURRENTTIME:
			print "The Creation time is in past and is correct :" + str(creationtime)
		else:
			print "The Creation time is not in past, Setting it to the current time as it is in future. "
			obj['ctime'] = CURRENTTIME
			with open(filename, 'r+') as f:
	 			f.seek(0)
	 			json.dump(obj, f)
		modificationtime = obj['mtime']
		if modificationtime <= CURRENTTIME: 
			print "The Modification time is in past and is correct :" + str(modificationtime)
		else:
			print "The Modification time is not in past, Setting it to the current time as it is in future. "
			obj['mtime'] = CURRENTTIME
			with open(filename, 'r+') as f:
	 			f.seek(0)
				json.dump(obj, f)
		print 'Time checking is complete' 

	# [4]check if each directory contains . and .. and their block numbers are correct
	try:
		parent = 0
		child = 0
		directory = 0
		for items in obj['filename_to_inode_dict']:
			if str(items['type']) == 'd' or str(items['type']) == 'f':
				filedirectorylist.append(str(items['location']))			
			if str(items['type']) == 'd':
				directory = 1				
				if str(items['name']) == '.':
					parent = items['location']
				if str(items['name']) == '..':
					child = items['location']

		# [5]f indirect is 1, data in the block pointed to by the location pointer is an array 
		if (directory == 1 and((parent == 0 and child!= 0) or (child ==0 and parent !=0))):
			print 'the directory is missing either a \' . \' or \' .. \' entry' 
			return 
		if parent != child:
			print 'the location of \' . \' and \' .. \' are not same , changing location of \' ..\' to ' + str(parent)
			for items in obj['filename_to_inode_dict']:
				if str(items['type']) == 'd':
					if str(items['name']) == '..':
						items['location'] = parent
		with open(filename, 'r+') as f:
	 			f.seek(0)
				json.dump(obj, f)
	except:
		print 'not a directory.. '

	# [6a,b,c]check if the size is valid for the number of block pointers in the location array
	if 'indirect' in obj:
		print 'indirect field detected with value : ' + str(obj['indirect'])
		if str(obj['indirect']) == '1':	
		  with open('fusedata.'+str(obj['location']),'r') as f:
			o=json.load(f)
			
			if isinstance(o,list):
				print 'The file at location contains array with value' + str(o)
			else :
				print 'The value is not an array ' 
			count = len(o)
			if obj['size'] > 0 and obj['indirect'] == 0 and obj['size'] > BLOCKSIZE:
        			print("File has indirect pointer set to 0 but file size exceeds block size")
     
     			if obj['indirect'] == 1 and obj['size'] > BLOCKSIZE*(count):
        			print("File has indirect pointer set to 1 but file size exceeds block size*number of blocks")
    	
      			if obj['indirect'] == 1 and obj['size'] < BLOCKSIZE*(count)-1:
        			print("File has indirect pointer set to 1 but file size is short of block size*number of blocks")
				 
				
		

proc = subprocess.Popen('ls', stdout=subprocess.PIPE)
output = proc.stdout.read().splitlines()
for i in output :
  if i == 'fusedata.0':
    with open(str(i), 'r') as f:
     objdata = json.load(f)
     freestart = objdata['freeStart']
     freeend = objdata['freeEnd']
     print 'super block found ' 	
     if int(objdata['devId']) == 20:
       print 'device id is 20. continuing the process'	+ 'freestart : ' + str(freestart) + 'freeend : ' + str(freeend)
     else:
	print 'device id is not 20 . exiting ...'
	exit()	
  print 'checking ' + str(i)	
  try:  
   with open(str(i), 'r') as f:
 	try:
		objdata = json.load(f)
 		checks(objdata,str(i))
	except:
		print ' No json data in ' + i			
		continue
  except:
	continue

#get unique elements in list
new = []
for i in filedirectorylist:
 if i not in new:
  new.append(i)
print 'files and directorys found in locations' + str(new)

checkloc=0
# [3a,b]validate the free blocks list, and check if its correct
missingblocks= []
for i in range(freestart,freeend):
	with open('fusedata.'+ str(i), 'r') as f:
		objdata = json.load(f)
		if new in objdata:
		 checkloc=1
		
		if len(objdata) < 400: 
			for x in range(0, len(objdata) -1):
				if objdata[x+1] - objdata[x] != 1:			
					y = objdata[x] 
					while (y != objdata[x+1] - 1):
						missingblocks.append(int(y) + int(1))
						y +=1
					print 'Few blocks are missing :' 
					print missingblocks
					print 'Adding missing blocks and free blocks to free list ....'
					freeblocks = objdata + missingblocks
					freeblocks.sort()
					with open('fusedata.'+ str(i), 'r+') as f:		
 						f.seek(0)
 						json.dump(freeblocks, f)



if checkloc == 1:
	print 'Files and directories in the free block list'
else:
	print 'No files or directories locations found on the free block lists'












