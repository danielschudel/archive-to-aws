#!/usr/bin/python

import archive
import sys
from getopt import getopt, GetoptError


def usage():
    """ Provide usage information when parameters are not complete """
    s =  "Usage: \n"
    s += "\tcreate   <directory>\n"
    s += "\tvalidate <archive file|directory>\n"
    s += "\tupload <aws options> <directory>\n"
    s += "\n"
    s += "Where <aws options> are each of the following:\n"
    s += " -v, --vault=VAULT (Required - Glacier vault name)\n"
    s += " -a, --access_key=ACCESS_KEY (if not specified will use standard Boto lookup)\n"
    s += " -s, --secret_key=SECRET_KEY (if not specified will use standard Boto lookup)\n"
    s += " -r, --region=REGION (if not specified, defaults to us-east-1)\n"
    s += "\n"
    sys.exit(s)

if len(sys.argv) < 2:
    usage()

argv = sys.argv[1:]
long_options = ['access_key=', 'secret_key=', 'region=', 'vault=', 'help']
try:
    opts, args = getopt(argv, "", long_options)
except GetoptError, e:
    usage()

options = dict()
options['vault'] = "NotSpecified"
options['region'] = "us-east-1"
options['access_key'] = None
options['secret_key'] = None
for option, value in opts:
    if option in ('--access_key'):
        options['access_key'] = value
    elif option in ('--secret_key'):
        options['secret_key'] = value
    elif option in ('--region'):
        options['region'] = value
    elif option in ('--vault'):
        options['vault'] = value
    elif option in ('--help'):
        usage()

if args[0]   == "create":
    a = archive.archive(args[1], options['vault'])
    a.create()
elif args[0] == "validate":
    a = archive.archive(args[1], options['vault'])
    a.validate()
elif args[0] == "upload":
    a = archive.archive(args[1], options['vault'])
    a.upload(options)
else:
    sys.exit("Did not understand {0}".format(command))
