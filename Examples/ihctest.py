"""
Test example showing how to use the ihcsdk to connect to the ihc controller
"""
from sys import argv
from ihcsdk.ihccontroller import IHCController

def on_ihc_change(ihcid, value):
    """Callback when ihc resource changes"""
    print("Resource change " + str(ihcid) + "->" + str(value))

def main():
    """Do the test"""
    if len(argv) != 5:
        print("Syntax: ihctest ihcurl username password resourceid")
        exit()
    resid = int(argv[4])
    ihc = IHCController(argv[1], argv[2], argv[3])
    if not ihc.Authenticate():
        print("Authenticate failed")
        exit()

    print("Authenticate succeeded\r\n")

    # read project
    project = ihc.GetProject()
    if project is False:
        print("Failed to read project")
    else:
        print("Project downloaded successfully")

    runtimevalue = ihc.GetRuntimeValue(resid)
    print("Runtime value: " + str(runtimevalue))
    ihc.SetRuntimeValueBool(resid, not runtimevalue)
    runtimevalue = ihc.GetRuntimeValue(resid)
    print("Runtime value: " + str(runtimevalue))

    ihc.AddNotifyEvent(resid, on_ihc_change)

    input()

main()
