import os

class archive:
    def __init__(self, dirOrFile):
        self.suffix = ".archive"
        if os.path.isdir(dirOrFile):
            self.directory = dirOrFile
            self.filename  = self.directory + self.suffix
        elif os.path.isfile(dirOrFile):
            self.filename  = dirOrFile
            self.directory = self.filename.strip(self.suffix);
        print "Filename = {0}".format(self.filename)
        print "Directory= {0}".format(self.directory)

    def create(self):
        if os.path.isfile(self.filename):
            print "Destination file {0} already exists. Stopping.".format(self.filename)
