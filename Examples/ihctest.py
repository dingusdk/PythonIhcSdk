import ihcsdk.ihcclient
import sys
from ihcsdk.ihccontroller import IHCController
from sys import argv

def IhcChange( id,v):
   print( "Resource change " + str( id) + "->" + str( v))


if len( argv) != 5:
    print( "Syntax: ihctest ihcurl username password resourceid")
    exit()

resid = int( argv[4])
ihc = IHCController( argv[1],argv[2],argv[3])
if not ihc.Authenticate():
    print( "Authenticate failed")
    exit()

print( "Authenticate succeeded\r\n")

value = ihc.GetRuntimeValue( resid)
print( "Runtime value: " + str( value))
ihc.SetRuntimeValueBool( resid,not value) 
value = ihc.GetRuntimeValue( resid)
print( "Runtime value: " + str( value))

ihc.AddNotifyEvent( resid,IhcChange)

input()

