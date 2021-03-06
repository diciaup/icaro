import os
import socket
import shutil
import json
import tarfile
import subprocess
import sys
import urlparse
import traceback

def ssh_execute(machine, command):
    bash = 'sshpass -p '+machine["password"]+' ssh -p'+str(machine["port"])+' '+machine["username"]+'@'+machine["addr"]+' '+command
    ssh = subprocess.Popen(bash.split(),
                           shell=False,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    result = ssh.stdout.readlines()
    if result == []:
        error = ssh.stderr.readlines()
        return {"status":False, "message":error}
    return {"status":True, "message":result}

def ssh_send(machine, file_path, destination, directory="-r"):
    if not os.path.isdir(file_path):
        directory = ""
    bash = 'sshpass -p '+machine["password"]+' scp '+directory+' -p'+str(machine["port"])+' '+file_path+' '+machine["username"]+'@'+machine["addr"]+':'+destination
    ssh = subprocess.Popen(bash.split(),
                           shell=False,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    result = ssh.stdout.readlines()
    if result == []:
        error = ssh.stderr.readlines()
        return {"status":False, "message":error}
    return {"status":True, "message":result}


def urldecode(url_data):
    return dict(urlparse.parse_qsl(url_data))


def checkPort(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    if result == 0:
        return True
    else:
        return False

def selfLocation():
    return os.path.dirname(os.path.realpath(__file__))

def bin_readLines(path):
    file = open(path, "r")
    content = file.readlines()
    file.close()
    return "".join(content).decode('utf-8')

def readLines(path):
    file = open(path, "r")
    content = file.readlines()
    file.close()
    return "".join(content)

def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z

def jsonUpdate(source, key, val):
    content = json.loads(readLines(source))
    content[key] = val
    fileWrite(source, json.dumps(content))

def rmdir(path):
    shutil.rmtree(path)

def jsonArrayUpdate(source, key, val):
    content = json.loads(readLines(source))
    for obj in content:
        obj[key] = val
    fileWrite(source, json.dumps(content))

def createFolder(path):
    if not os.path.exists(path):
	os.mkdir(path)

def bin_fileWrite(file, content):
    if os.path.dirname(file) != "":
        mkDir(os.path.dirname(file))
    file = open(file, "wb")
    file.write(content.encode('utf-8'))
    file.close()

def fileWrite(file, content):
    if os.path.dirname(file) != "":
        mkDir(os.path.dirname(file))
    file = open(file, "w")
    file.write(content)
    file.close()

def importer(source, destination):
    fileWrite(destination,readLines(source))

def mkDir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def insertIntoFile(offset1, stringToInsert, file):
    content = readLines(file)
    if content.strip().find(stringToInsert.strip()) == -1:
            n = content.find(offset1)
            if n != -1:
                    while (content[n] != "{"):
                            n += 1
                    content = content[:n+1] + stringToInsert + content[n+1:]
                    fileWrite(file, content)

def get_sql(file):
    return readLines("sql/"+file+".sql")

def line_prepender(filename, line):
    with open(filename, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(line.rstrip('\r\n') + '\n' + content)

def copytree(source, destination):
    if not os.path.exists(destination):
        shutil.copytree(source, destination)

def getHome():
    return os.path.expanduser("~")

#--Static Body Defintion-----

class BodyRequestTypeWrong(Exception):
    def __init__(self, excepted_type, found_type):
        traceback.print_exc()
        print("Excepted type "+ excepted_type+", found type " + found_type.__name__)


class BodyRequestVioletedLengthConstraint(Exception):
    def __init__(self, excepted_length, found_length, key):
        traceback.print_exc()
        print("Key " + key + " max length excepted " + str(excepted_length) +", found length " + str(found_length))


class BodyRequestWrongKey(Exception):
    def __init__(self, key_found):
        traceback.print_exc()
        print("Wrong_key found " + key_found)


class UnknowStaticLevel(Exception):
    def __init__(self, static_level_found):
        traceback.print_exc()
        print("Unknow static level specified: "+ static_level_found)

class UnpermittedValue(Exception):
    def __init__(self, key, value, permitted_val):
        traceback.print_exc()
        print("Unpermitted " + key + ": " + value + ", permitted values: ")
        for val in permitted_val:
            print val

class WrongOrder(Exception):
    def __init__(self, keys):
        traceback.print_exc()
        print("Wrong parameter order!! \n Correct Order: ")
        for key in keys:
            print key


class MissingKeys(Exception):
    def __init__(self, missing_keys):
        traceback.print_exc()
        print("Missing keys from structure: ")
        for key in missing_keys:
            print(key)


def first_check(data, body_draft = None):
    for key, value in data.iteritems():
        if key not in body_draft:
            raise BodyRequestWrongKey(key)
        if len(value) > body_draft[key]["length"]:
            raise BodyRequestVioletedLengthConstraint(body_draft[key]["length"], len(value), key)
        if type(value).__name__ != body_draft[key]["type"]:
            raise BodyRequestTypeWrong(body_draft[key]["type"], type(value))
        if "permitted_val" in body_draft[key] and value not in body_draft[key]["permitted_val"]:
            raise UnpermittedValue(key, value, body_draft[key]["permitted_val"])


def second_check(data, body_draft = None):
    pass


def third_check(data, body_draft = None):
    pass


def check_body(data, body_draft = None, static_level = 1):
    if body_draft:
        first_check(data, body_draft)
    if static_level >= 2:
        second_check(data, body_draft)
    if static_level == 3:
        third_check(data, body_draft)
    return data


def get_body(req, body_draft = None, static_level = 1):
    """
    body_draft -> a structure of your body like this:
        {
        "key1": {"type": "str", "length": 50, "permitted_val": []},
        "key2": {"type": "str", "length": 50}
         ecc...
        }
    static_level:
        1 -> make static only type, length and permitted_val
        2 -> you must enter always all keys into body
        3 -> the same of 2 + the order is static
    """
    return check_body(urldecode(req.stream.read()), body_draft, static_level)
