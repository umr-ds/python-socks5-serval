#!/usr/bin/python2.7
#encoding=utf-8

import socket
from threading import Thread
import sys
import signal
import string
import subprocess


SOCKTIMEOUT=5
RESENDTIMEOUT=300

VER="\x05"
METHOD="\x00"

SUCCESS="\x00"
SOCKFAIL="\x01"
NETWORKFAIL="\x02"
HOSTFAIL="\x04"
REFUSED="\x05"
TTLEXPIRED="\x06"
UNSUPPORTCMD="\x07"
ADDRTYPEUNSPPORT="\x08"
UNASSIGNED="\x09"

_LOGGER=None

class Log:
	WARN="[WARN:]"
	INFO="[INFO:]"
	ERROR="[ERROR:]"
	def write(self,message,level):
		pass

class SimpleLog(Log):
	import sys
	def __init__(self,output=sys.stdout):
		self.__output=output
		self.show_log=True

	def write(self,message,level=Log.INFO):
		if self.show_log:
			self.__output.write("%s\t%s\n" %(level,message))

def getLogger(output=sys.stdout):
	global _LOGGER
	if not _LOGGER:
		_LOGGER=SimpleLog(output)
	return _LOGGER


class SocketTransform(Thread):
	def __init__(self,src,dest_ip,dest_port,bind=False, serval_connection=False):
		Thread.__init__(self)
		self.dest_ip=dest_ip
		self.dest_port=dest_port
		self.src=src
		self.bind=bind
		self.setDaemon(True)
		self.serval=serval_connection

	def run(self):
		try:
			self.resend()
		except Exception,e:
			getLogger().write("Error on SocketTransform %s" %(e.message,),Log.ERROR)
			self.sock.close()
			self.dest.close()

	def resend(self):
		self.sock=self.src
		if self.bind:
			getLogger().write("Waiting for the client")
			self.sock,info=sock.accept()
			getLogger().write("Client connected")

		if self.serval:
			getLogger().write("Starting serval mode " + self.dest_ip)

			p = subprocess.Popen(
                        ["servald", 'msp', 'connect', self.dest_ip, str(self.dest_port)],
                     stdout = subprocess.PIPE,
                     stdin = subprocess.PIPE)
			getLogger().write("Starting Resending")
			self.sock.settimeout(RESENDTIMEOUT)
			#self.dest.settimeout(RESENDTIMEOUT)
			UniversalResender(self.sock,p.stdin).start()
			UniversalResender(p.stdout,self.sock).start()

		else:
			self.dest=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			self.dest.connect((self.dest_ip,self.dest_port))

			getLogger().write("Starting Resending")
			self.sock.settimeout(RESENDTIMEOUT)
			self.dest.settimeout(RESENDTIMEOUT)
			UniversalResender(self.sock,self.dest).start()
			UniversalResender(self.dest,self.sock).start()

class UniversalResender(Thread):
	def __init__(self,src,dest):
		Thread.__init__(self)
		self.src=src
		self.setDaemon(True)
		self.dest=dest

	def run(self):
		try:
			self.resend(self.src,self.dest)
		except Exception,e:
			getLogger().write("Connection lost %s" %(e.message,),Log.ERROR)
			self.src.close()
			self.dest.close()

	def resend(self,src,dest):
		if isinstance(src, file):
			data=src.read(10)
		else:
			data=src.recv(10)
		while data:
			if isinstance(dest, file):
				dest.write(data)
			else:
				dest.sendall(data)

			if isinstance(src, file):
				data=src.read(10)
			else:
				data=src.recv(10)

		src.close()
		dest.close()
		getLogger().write("Client quit normally\n")


def create_server(ip,port):
	transformer=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	transformer.bind((ip,port))
	signal.signal(signal.SIGTERM,OnExit(transformer).exit)
	transformer.listen(1000)
	while True:
		sock,addr_info=transformer.accept()
		sock.settimeout(SOCKTIMEOUT)
		getLogger().write("Got one client connection")
		try:
			serval_connection = False
			ver,nmethods,methods=(sock.recv(1),sock.recv(1),sock.recv(1))
			sock.sendall(VER+METHOD)
			cmd, ver, atyp, rsv=(sock.recv(1),sock.recv(1),sock.recv(1),sock.recv(1))
			dst_addr=None
			dst_port=None
			atyp = sock.recv(1) # TODO: dirty - debug
			getLogger().write("Checking atyp: " + str(ord(atyp)))

			if atyp=="\x01":#IPV4
				dst_addr,dst_port=sock.recv(4),sock.recv(2)
				dst_addr=".".join([str(ord(i)) for i in dst_addr])
			elif atyp=="\x03":#Domain
				addr_len=ord(sock.recv(1))
				dst_addr,dst_port=sock.recv(addr_len),sock.recv(2)
				dst_addr="".join([unichr(ord(i)) for i in dst_addr])
				if addr_len == 64:
					if all(c in string.hexdigits for c in dst_addr):
						serval_connection=True

			elif atyp=="\x04":#IPV6
				dst_addr,dst_port=sock.recv(16),sock.recv(2)
				tmp_addr=[]
				for i in xrange(len(dst_addr)/2):
					tmp_addr.append(unichr(ord(dst_addr[2*i])*256+ord(dst_addr[2*i+1])))
				dst_addr=":".join(tmp_addr)
			else:
				getLogger().write("No known atyp" + atyp)
			dst_port=ord(dst_port[0])*256+ord(dst_port[1])
			getLogger().write("Client wants to connect to %s:%d" %(dst_addr,dst_port))
			server_sock=sock
			server_ip="".join([chr(int(i)) for i in ip.split(".")])

			if cmd=="\x02":#BIND
				#Unimplement
				sock.close()
			elif cmd=="\x03":#UDP
				#Unimplement
				sock.close()
			elif cmd=="\x01":#CONNECT
				sock.sendall(VER+SUCCESS+"\x00"+"\x01"+server_ip+chr(port/256)+chr(port%256))
				getLogger().write("Starting transform thread")
				SocketTransform(server_sock,dst_addr,dst_port,serval_connection=serval_connection).start()
			else:#Unspport Command
				sock.sendall(VER+UNSPPORTCMD+server_ip+chr(port/256)+chr(port%256))
				sock.close()
		except Exception,e:
			getLogger().write("Error on starting transform:"+e.message,Log.ERROR)
			sock.close()

class OnExit:
	def __init__(self,sock):
		self.sock=sock

	def exit(self):
		self.sock.close()


if __name__=='__main__':
	try:
		ip="0.0.0.0"
		port=1080
		create_server(ip,port)
	except Exception,e:
		getLogger().write("Error on create server:"+e.message,Log.ERROR)
