import os
import sys
import hashlib
import tarfile
import boto
try:
    import boto.glacier
except:
    sys.exit("Failed to import a version of boto that has Glacier Support")

oneGB = 1*1024*1024*1024
suggestedMaxSize = oneGB

class archive:
    def __init__(self, dirOrFile, vault):
        self.suffix = ".archive.tar"
        if os.path.isdir(dirOrFile):
            directory = os.path.abspath(dirOrFile)
            filename  = directory + self.suffix
        elif os.path.isfile(dirOrFile):
            filename  = os.path.abspath(dirOrFile)
            directory = filename.strip(self.suffix)
        else:
            sys.exit("Failed to find {0}".format(dirOrFile))

        # Partial name of the archive
        self.archiveName          = os.path.basename(directory)
        # Full name of the directory to be archived
        self.archiveDirectory     = directory
        # Full name of the archive file
        self.archiveFile          = filename
        # Archive needs to be created relative to here
        self.parent               = os.path.dirname(directory)
        # Accounting file to be included in the archive
        self.internalAccounting   = directory + "/files.sha1sum"
        # Accounting file to be stashed away
        self.externalAccounting   = filename  + ".sha1sum"
        # Accounting file in S3
        self.bucketName           = "glacier_archives"
        self.glacierVault         = vault
        self.externalAccountingS3 = "Vault-{0}/{1}".format(self.glacierVault,os.path.basename(self.externalAccounting))

        print "Important variables"
        print " Vault       = {0}".format(self.glacierVault)
        print " Bucket      = {0}".format(self.bucketName)
        print " ArchiveName = {0}".format(self.archiveName)
        print " ArchiveDir  = {0}".format(self.archiveDirectory)
        print " ArchiveFile = {0}".format(self.archiveFile)
        print " Parent      = {0}".format(self.parent)
        print " Internal    = {0}".format(self.internalAccounting)
        print " External    = {0}".format(self.externalAccounting)
        print " ExternalS3  = {0}".format(self.externalAccountingS3)

    def validate(self):
        print "Performing Sanity checks"
        self.validateSanityChecks()
        print "Validating archive"
        self.validateArchive()

    def lookupSha1sum(self, filename):
        f = open(self.externalAccounting, 'r')
        for line in f:
            sum, file = line.split("  ")
            file = file.strip()
            if file == filename:
                f.close()
                return sum
        f.close()
        return 0

    def validateArchive(self):
        # look through self.externalAccounting and match on self.archiveFile
        # pull out sha1sum and compare
        recorded = self.lookupSha1sum(os.path.basename(self.archiveFile))
        computed = self.computeSha1sum(self.archiveFile)
        if (recorded == computed):
            print " Archive checksum matches local file"
        else:
            print " Computed = {0}".format(computed)
            print " Recorded = {0}".format(recorded)
            sys.exit("Sums do not match, exiting")

    def validateSanityChecks(self):
        if False == os.path.isfile(self.archiveFile):
            sys.exit("Archive {0} does not exist".format(self.archiveFile))
        if False == os.path.isfile(self.externalAccounting):
            sys.exit("Archive {0} does not exist".format(self.externalAccounting))

    def create(self):
        print "Performing Sanity checks"
        self.sanityCheckCreate()
        print "Looking for existing sums to check"
        self.checkExistingSums()
        print "Computing and recording checksums"
        self.computeAndRecordSums()
        print "Creating archive"
        self.createArchive()
        print "Recording checksum of archive"
        self.recordArchiveChecksum()

    def createArchive(self):
        tf = tarfile.TarFile(self.archiveFile, mode='w', dereference=True)
        tf.add(self.archiveDirectory, self.archiveName)
        tf.close()

    def recordArchiveChecksum(self):
        directoryLen = len(self.parent) + 1
        pp = self.archiveFile[directoryLen:]
        ea = open(self.externalAccounting, 'a')
        ea.write("{0}  {1}\n".format(self.computeSha1sum(self.archiveFile), pp))
        ea.close()

    def computeAndRecordSums(self):
        ia = open(self.internalAccounting, 'w')
        ea = open(self.externalAccounting, 'w')
        directoryLen = len(self.parent) + 1
        total=0
        for dirpath, dirnames, filenames in os.walk(self.archiveDirectory):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if (fp == self.internalAccounting):
                    continue
                if (os.path.isfile(fp)):
                    total += 1

        remain = total
        for dirpath, dirnames, filenames in os.walk(self.archiveDirectory):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if (fp == self.internalAccounting):
                    continue
                if (os.path.isfile(fp)):
                    sum = self.computeSha1sum(fp)
                    pp = fp[directoryLen:]
                    ia.write("{0}  {1}\n".format(sum, pp))
                    ea.write("{0}  {1}\n".format(sum, pp))
                    print "\r {0:<10} {1}".format(remain, sum),
                    remain -= 1

        ia.close()
        ea.close()
        print "\r {0} sums recorded                                               ".format(total)

    def computeSha1sum(self, filepath):
        sha1 = hashlib.sha1()
        f = open(filepath, 'rb')
        try:
            sha1.update(f.read())
        finally:
            f.close()
            return sha1.hexdigest()

    def checkExistingSums(self):
        # Look inside self.archiveDirectory for sha1sum files and check them
        pass

    def sanityCheckCreate(self):
        if os.path.isfile(self.archiveFile):
            sys.exit("Destination file {0} already exists. Stopping.".format(self.archiveFile))

        if False == os.path.isdir(self.archiveDirectory):
            sys.exit("Directory {0} does not exist. Stopping.".format(self.archiveDirectory))

        size = self.getSize(self.archiveDirectory)
        print " Size        = {0}".format(size)
        if size > suggestedMaxSize:
            print "Your archive will be about {0} GB large.".format(size/oneGB)
            print "Consider breaking it up into smaller pieces."

    def getSize(self, start_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if (os.path.isfile(fp)):
                    total_size += os.path.getsize(fp)
        return total_size

    def uploadSanityCheck(self, options):
        abort = False;
        for k in ['region', 'vault']:
            if False == options.has_key(k):
                print(" Need to specify --{0}".format(k))
                abort = True

        if False == os.path.isfile(self.archiveFile):
            print " Archive file {0} does not exist".format(self.archiveFile)
            abort = True

        if False == os.path.isfile(self.externalAccounting):
            print " Accounting file {0} does not exist".format(self.externalAccounting)
            abort = True

        print " Boto version {0}".format(boto.Version)

        if abort:
            sys.exit(" Aborting...")

    def uploadToGlacier(self, srcfile, options):
        print "Uploading {0} to glacier://{1}".format(srcfile, self.glacierVault)

        glacier_vault = self.glacierConnection.get_vault(self.glacierVault)
        # TODO - Save archiveId vault.name and full vault.arn in externalAccountingFile
        # TODO - use try/catch/except to catch failures
        archiveId = glacier_vault.upload_archive(srcfile)

    def uploadToS3(self, destfile, srcfile):
        print "Uploading {0} to s3://{1}/{2}".format(srcfile, self.bucketName, destfile)
        print " Preparing file for upload to {0}".format(destfile)
        k = self.s3Bucket.new_key(destfile)
        k.set_contents_from_filename(srcfile, reduced_redundancy=True, cb=submit_cb, num_cb=100)
        pass

    def makeConnections(self, options):
        print " Connecting to S3"
        self.s3Connection = boto.connect_s3(aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key)
        print " Creating bucket s3://{0}".format(self.bucketName)
        self.s3Bucket = self.s3Connection.create_bucket(self.bucketName)
        if None != self.s3Bucket.get_key(self.externalAccountingS3):
            sys.exit(" File is already in S3")

        print " Connecting to Glacier"
        self.glacierConnection = boto.glacier.connect_to_region(options['region'], aws_access_key_id=options['access_key'], aws_secret_access_key=options['secret_key'])
        inThere = False
        for vault in self.glacierConnection.list_vaults():
            if self.glacierVault == vault.name:
                inThere = True
                break

        if inThere == False:
            sys.exit(" Vault {0} is not in Glacier at the moment. Aborting.".format(self.glacierVault))


    def upload(self, options):
        print "Performing Sanity checks"
        self.uploadSanityCheck(options)

        self.aws_access_key_id = None
        if options.has_key('access_key'):
            self.aws_access_key_id = options['access_key']

        self.aws_secret_access_key = None
        if options.has_key('secret_key'):
            self.aws_secret_access_key = options['secret_key']

        print "Making connections to AWS"
        self.makeConnections(options)

        # Upload the archive
        self.uploadToGlacier(self.archiveFile, options)

        # Upload the accounting file
        self.uploadToS3(self.externalAccountingS3, self.externalAccounting)

def submit_cb(bytes_so_far, total_bytes):
    print '%d bytes transferred / %d bytes total' % (bytes_so_far, total_bytes)
