import json
import requests
import os
import shutil
import icaro.core.utils as utils
import versioning
import tarfile
import distutils.dir_util as dir_util
import testing
import icaro.caching as caching
from libs import LibsController
from icaro.core.virtualarea.workarea import Workarea
from icaro.core.virtualarea.main import Virtualarea
from icaro.core.virtualarea.container import Container
from icaro.core.virtualarea.monitor import Monitor
from icaro.core.nginx.main import Nginx
from icaro.core.connectors.machine import Machine
from icaro.validator.main import Validator
from icaro.controller.deployment import EnvController
from testing import Test

class Controller:
    def __init__(self):
        self.settings = Validator().settings(utils.readLines("settings.json"))
        self.virtualarea = Virtualarea(self.settings)
        self.monitor = Monitor(self.virtualarea)
        self.workarea = Workarea(self.virtualarea)

    def __build_env(self):
        if self.settings["session_engine"] == "icaro":
            if os.fork() != 0:
                os.system("uwsgi --enable-threads --http-socket 0.0.0.0:5000 --wsgi-file "+os.path.dirname(caching.__file__)+"/manager.py --callable api --logto 127.0.0.1:1717")
        if os.fork() != 0:
            os.system("uwsgi --udp 0.0.0.0:1717")

    def __valid_machine(self, machine_name, node):
        print "Validating "+machine_name+"..."
        if machine_name != "local":
            machine = Machine(self.settings["machines"][machine_name], machine_name, node)
            if machine.check():
                return machine
        else:
            return "local"

    def libs(self, command, query):
        return getattr(LibsController(self.virtualarea), command)(query)
    
    def run_containers(self):
        containers = {}
        for container in self.virtualarea.containers:
            containers = self.run_container(container,track = containers)
        return containers

    def run_container(self, container, track = {}):
        track[container["name"]] = []
        for node in range(0, container["nodes"]):
            container_obj = Container(self.settings["project_name"], self.virtualarea, container, node, self.__valid_machine(container["machine"], node))
            container_obj.shut()
            track[container["name"]].append(container_obj.run())
        return track

    def __tree_build(self):
        """
        Scope:
            Build virtualarea and workarea folder
        """
        self.workarea.gen_folders()
        self.workarea.gen_files()
        self.virtualarea.create()

    def build_all(self):
        """
        Output -> json built
        Scope:
            Build all containers creating monitor and building nginx
        """
        Validator().machine(self.settings["machines"])
        self.__tree_build()
        built = self.run_containers()
        self.monitor.create(built)
        Nginx(self.virtualarea, built).build()
        return built

    def build(self, containerName):
        """
        Input -> containerName
        Output -> json built
        Scope:
            Build a single container creating monitor and building nginx
        """
        container = self.virtualarea.get_container_by_name(containerName)
        Validator().machine(self.settings["machines"])
        self.__tree_build()
        built = self.run_container(container)
        if self.monitor.get():
            self.monitor.update(built)
        else:
            self.monitor.create(built)
        Nginx(self.virtualarea, built).build()
        return built

    def whereismyelement(self, type, elementName):
        """Return list of node name"""
        containers = self.virtualarea.get_element(type, elementName).where_am_i()
        return json.dumps(containers)

    def run(self, type, elementName, version):
        element = self.virtualarea.get_element(type, elementName)
        if version == "current":
            element.run(element.current)
        elif version == "all":
            element.run_all_versions()
        else:
            element.run(version)        

    def check_machines(self):
        for machine_name, machine in self.settings["machines"].iteritems():
            print("Checking "+machine_name+"...")
            if Machine(machine, machine_name).check():
                print machine_name+"-->OK"
            else:
                print "Machine configured but not turned on remote machine"

    def __config_machine(self, machine_name, machine):
        machine = Machine(machine, machine_name)
        machine.configure(self.settings["server_addr"])
    
    def commit_settings(self):
        utils.fileWrite("settings.json", json.dumps(self.settings))

    def config_machines(self):
        """
        Transport all connectors to relative machines
        """
        utils.mkDir(".connections")
        for machine_name, machine in self.settings["machines"].iteritems():
            print("Configuring "+machine_name+"...")
            self.__config_machine(machine_name, machine)

    def update(self):
        """
        Update workarea if settings it's been changed
        """
        self.workarea.gen_folders()
        self.workarea.gen_files()
        return "Update -> OK"

    def htop(self, containerName):
        """
        Show process and performance of a container
        """
        node = containerName.split("-").pop()
        containerName = containerName.split("-")[:-1]
        containerName = "-".join(containerName)
        container = self.virtualarea.get_container_by_name(containerName)
        return Container(self.settings["project_name"], self.virtualarea, container, node, "local").htop()

    def env(self, action, name, secondEnv = None):
        """
        Enviroment commands
        """
        EnvController(self, action, name, secondEnv)

    def clean(self, type):
        """
        Hard => clean virtual area and all containers
        Soft => clean virtual area
        """
        if type == "hard":
            os.system("rm -rf "+self.virtualarea.path)
        elif type == "soft":
            os.system("rm -rf "+self.virtualarea.path)

    def run_all_in_container(self, containerName):
        for element in self.virtualarea.get_container_node_by_name(containerName).get_all_obj_elements():
            element.run_all_versions()

    def run_all(self):
        self.__build_env()
        for element in self.virtualarea.get_all_elements():
            element.run_all_versions()

    def test(self):
        Test(self).start()

    def upgrade(self, type, elementName):
        """Upgrade element current version"""
        self.virtualarea.get_element(type, elementName).upgrade()
