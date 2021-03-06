import sys
import icaro.core.utils as utils
import json

class Validator:
    def __init__(self):
        self.settings_template = {}

    def settings(self, settings):
        self.settings = self.__basic_validator(settings)
        return self.settings

    def machine(self, machines):
        self.__machines_validator(machines)
        print "Machines --> OK"
        return True

    def __machines_validator(machines):
        for machine_name, machine in machines.iteritems():
            command = utils.ssh_execute(machine, "ls /")
            if not command["status"]:
                print "Invalid configuration for "+machine_name+". Details: "+",".join(command["message"])
                sys.exit()

    def __basic_validator(settings):
        try:
            settings = json.loads(settings)
        except Exception as e:
            print "Error reading config, details: " + e.message
            sys.exit()
        return settings
