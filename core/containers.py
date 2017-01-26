import json
import os
import shutil
import subprocess
import docker
import uuid
import utils

virtualarea = utils.getHome() + "/icaro/"

def tracker(container, type, port, config):
    for element in container[type]:
        obj = {'type': type, 'port': port, 'name': element["name"]}
        config.append(obj)
        port += 1
    return config

def createContainer(container, path, port):
    config = []
    dockerfile = "FROM ubuntu\nFROM python:2.7-onbuild\n"#FROM glatard/matlab-compiler-runtime-docker\n
    config = tracker(container, "apis", port, config)
    config = tracker(container, "pages", port+len(config), config)
    utils.fileWrite(path + "/config.icaro", json.dumps(config))
    for element in config:
        dockerfile += "EXPOSE " + str(element["port"]) + "\n"
    dockerfile += "EXPOSE 10036\n"
    dockerfile += 'CMD ["apt-get", "install", "update"]\n'
    dockerfile += 'CMD ["apt-get", "install", "upgrade"]\n'
    dockerfile += 'CMD ["uwsgi", "--enable-threads", "--http-socket", "0.0.0.0:10036", "--wsgi-file", "controller.py", "--callable", "api"]'
    return dockerfile

def clearVersion(folder, versions):
    #versions is number of version from last to preserve
    if len(list(os.walk(folder))) > versions:
        shutil.rmtree(list(os.walk(folder))[0])

def createRequirements():
    return "falcon==1.1.0\r\nuwsgi==2.0.14"

def controller(destination):
    key = str(uuid.uuid4())
    utils.importer(utils.selfLocation() + "/controller.py", destination + "/controller.py")
    utils.line_prepender(destination + "/controller.py", "p_key = '" + key +"'\r\n")
    utils.fileWrite(destination + "/controller.icaro", json.dumps({'key': key, 'addr':''}))

def genFolders(container, type, destination):
    print "Generating VirtualArea - " + container["name"] + "'s " + type
    for element in container[type]:
        utils.mkDir(destination + "/" + type + '/' + element['name'] + '/' + element['version'])
        utils.importer(type + "/" + element["name"] + ".py", destination + "/" + type + '/' + element['name'] + '/' + element['version'] + "/" + element["name"] + ".py")
    if type == "pages":
        utils.copytree("widgets", destination + "/widgets")
        utils.copytree("pages/libraries", destination + "/pages/libraries")

def createMonitor(destination, containers):
    for container in containers:
        i=0
        for node in containers[container]:
            elements = json.loads(utils.readLines(destination + "/" + container + "-" + str(i) + "/config.icaro"))
            node["elements"] = elements
            i+=1
    utils.fileWrite(destination + "/monitor.icaro", json.dumps(containers))
    return containers

def genVirtualArea(settings):
    for container in settings["containers"]:
        for node in range(0, container["nodes"]):
            destination = virtualarea + settings['project_name'] + '/' + container["name"] + "-" + str(node)
            genFolders(container, "apis", destination)
            genFolders(container, "pages", destination)
            #clearVersion(destination, 10)
            utils.fileWrite(destination + "/requirements.txt", createRequirements())
            utils.fileWrite(destination + "/Dockerfile", createContainer(container, destination, 8000))
            controller(destination)
            utils.importer(utils.selfLocation() + "/core.rb", destination + "/" + "core.rb")

def buildContainer(client, node, containerName, project_name):
    print "Building " + containerName + "..."
    return client.images.build(path = virtualarea + project_name + "/" + containerName + "-" + str(node))

def runContainer(container, project_name, node):
    client = docker.from_env()
    hostname = str(uuid.uuid4()) + "-host"
    containerDocker = client.containers.run(buildContainer(client, node, container["name"], project_name).id,
                                                     detach = True,
                                                     name = project_name + "-" + container["name"] + "-" + str(node),
                                                     hostname = hostname,
                                                     network_mode="bridge",
                                                     mem_limit = container["memory_limit"])
    print "Running " + container["name"] + " - node" + str(node)  + "..."
    name = containerDocker.name
    addr = client.containers.get(containerDocker.id).attrs["NetworkSettings"]["IPAddress"]
    status = containerDocker.status
    utils.jsonArrayUpdate(virtualarea + project_name + "/" + container["name"] + "-"+ str(node) +"/config.icaro", "addr", addr)
    return {"addr": addr, "status": status}

def shutNode(container, node, project_name):
    client = docker.from_env()
    client.containers.get(project_name + "-" + container + "-" + str(node)).stop(timeout=1)
    client.containers.get(project_name + "-" + container + "-" + str(node)).remove(v=True)
    return project_name + "-" + container + "-" + str(node)

def runContainers(settings):
    containers = {}
    for container in settings["containers"]:
        containers[container["name"]] = []
        for node in range(0, container["nodes"]):
            containers[container["name"]].append(runContainer(container, settings["project_name"], node))
    createMonitor(virtualarea + settings["project_name"], containers)
    return containers

def shutNodes(settings):
    monitors = []
    config = json.loads(utils.readLines(virtualarea + settings["project_name"] + "/monitor.icaro"))
    for container in config:
        for node in range(0, len(config[container])):
            shutNode(container, node, settings["project_name"])
        if os.path.isfile(virtualarea + settings["project_name"] + "/monitor.icaro"):
            monitors = json.loads(utils.readLines(virtualarea + settings["project_name"] + "/monitor.icaro"))
            #for monitor in monitors:
            #    monitors.remove(monitor) if monitor["name"] == containerName else monitors
            #    utils.fileWrite(virtualarea + settings["project_name"] + "/monitor.icaro", json.dumps(monitors))"""
