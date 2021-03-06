import shutil
import os
import sys
import json
import icaro.core.utils as utils
import importlib

def pack_libs(libs):
    for lib in libs:
        os.system("sudo apt-get -y -f install " + lib)

def dockerfile(packages):
    result = ""
    for package in packages:
        module = importlib.import_module('icaro.packages.'+package["lang"]+"."+package["package"])
        result += module.dockerfile()
    return result

def include(packages, destination):
    for package in packages:
        module = importlib.import_module('icaro.packages.'+package["lang"] + "." + package["package"])
        module.include(destination)

def lib(packages):
    result = []
    for package in packages:
        module = importlib.import_module('icaro.packages.' + package["lang"] + "." + package["package"])
        result.append({"lang": package["lang"], "content": module.lib()})
    return result

def commands(packages):
    result =  ""
    for package in packages:
        module = importlib.import_module('icaro.packages.' + package["lang"] + "." + package["package"])
        for command in module.commands():
            result += "CMD " + json.dumps(command.split(" ")) + "\r\n"
    return result
