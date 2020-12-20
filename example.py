"""
Test example showing how to use the ihcsdk to connect to the ihc controller
To run the example create a file '.parameters' in this folder and add:
ihcurl username password resourceid
The resourceid is an ihc resource id of any boolean resource in you controller.
The resource will be toggled when the test starts, and after this you can set it
using '1' and '2'. 'q' to quit
"""
from datetime import datetime

from ihcsdk.ihccontroller import IHCController


def main():
    """Do the test"""

    starttime = datetime.now()

    def on_ihc_change(ihcid, value):
        """Callback when ihc resource changes"""
        print("Resource change " + str(ihcid) + "->" + str(value) +
              " time: " + gettime())

    def gettime():
        dif = datetime.now() - starttime
        return str(dif)

    cmdline = open(".parameters", "rt").read()
    args = cmdline.split(' ')
    if len(args) != 4:
        print("The '.parameters' file should contain: ihcurl username password resourceid")
        exit()
    url = args[0]
    resid = int(args[3])
    ihc = IHCController(url, args[1], args[2])
    if not ihc.authenticate():
        print("Authenticate failed")
        exit()

    print("Authenticate succeeded\r\n")

    # read the ihc project
    project = ihc.get_project()
    if project is False:
        print("Failed to read project")
    else:
        print("Project downloaded successfully")

    log = ihc.client.get_user_log()
    if log:
        print("log: " + log)

    info = ihc.client.get_system_info()
    print( info)

    runtimevalue = ihc.get_runtime_value(resid)
    print("Runtime value: " + str(runtimevalue))
    ihc.set_runtime_value_bool(resid, not runtimevalue)
    runtimevalue = ihc.get_runtime_value(resid)
    print("Runtime value: " + str(runtimevalue))

    # ihc.client.enable_runtime_notifications( resid)
    # changes = ihc.client.wait_for_resource_value_changes( 10)
    # print( repr( changes))

    ihc.add_notify_event(resid, on_ihc_change, True)

    while True:
        i = input()
        if i == "1":
            starttime = datetime.now()
            ihc.set_runtime_value_bool(resid, False)
            continue
        if i == "2":
            starttime = datetime.now()
            ihc.set_runtime_value_bool(resid, True)
            continue
        if i == "q":
            break
    ihc.disconnect()


main()
