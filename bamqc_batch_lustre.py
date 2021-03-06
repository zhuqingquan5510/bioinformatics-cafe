#!/home/berald01/.local/bin/python


import subprocess
import os
import sys

if len(sys.argv) != 2:
    sys.exit(
    """
DESCRIPTION
    Execute bamqc.py on all the bam files under <BAMDIR> (searched recursivley)
    Output files written to BAMQCDIR on lustre, scp'd to LOCALHOST:LOCALDIR and
    uploaded to postgres

    bamqc.py is executed on lustre using bsub.
    
USAGE
    bamqc_batch_lustre.py <BAMDIR>
    
EXAMPLES
    ## Execute on lustre (e.g. mac office):
    bamqc_batch_lustre.py /lustre/sblab/berald01/repository

TODO
    Finer regulation of how dirs are scanned. Allow for exclude dirs and multiple dirs. 
    """)

BAMQCDIR= '/lustre/sblab/berald01/bamqc' ## dir where output files will be. NB: Content of this dir will be erased at the beginning of each execution of bamqc_batch_lustre.py
BAMDIR= sys.argv[1] ## Top dir where to serach for bams.
LOCALHOST= '10.20.13.11' ## Where the output of bamqc will be scp'd
LOCALDIR= '/tmp/' ## 
UPLOAD_SCRIPT= '/Users/berald01/svn_checkout/postgresql-setup-cruk/upload_bamqc_script.sql' ## This script will be run by psql to upload the concatenated outputs.

p= subprocess.Popen('find %s' %(BAMDIR), shell= True, stdout=subprocess.PIPE)
allfiles= p.stdout.read().strip()
allfiles= allfiles.split('\n')
bamfiles= sorted([x for x in allfiles if x.endswith('.bam')])
if not os.path.exists(BAMQCDIR):
    os.makedirs(BAMQCDIR)
for f in os.listdir(BAMQCDIR):
    if f.endswith('.bamqc.tsv'):
        os.remove(os.path.join(BAMQCDIR, f))

for i in range(0, len(bamfiles)):
    (bampath, bam)= os.path.split(bamfiles[i])
    ## Check there are no bam files with the same name otherwise the outputs will ovewrite each other
    suffix= 0
    for x in bamfiles[0:i]:
        (other_path, other_bam)= os.path.split(x)
        if bam == other_bam:
            suffix += 1
    if suffix == 0:
        suffix= ''
    else:
        suffix= '.' + str(suffix)
    bamqc_out= os.path.join(BAMQCDIR, os.path.splitext(bam)[0] + suffix + '.bamqc.tsv')
    bamqc_log= os.path.join(BAMQCDIR, os.path.splitext(bam)[0] + suffix + '.bamqc.log')
    jobname= 'jobbamqc_' + bam
    cmd= 'bsub -R "rusage[mem=1024]" -J %s -o %s "bamqc.py --nograph --noheader -i %s -o %s" &> /dev/null' %(jobname, bamqc_log, os.path.join(bampath, bam), bamqc_out)
    p= subprocess.Popen(cmd, shell= True)

cmd= """bsub -o scp.log -R "rusage[mem=1024]" -w 'ended("jobbamqc_*")' '
    cat %(bamqcdir)s/*.bamqc.tsv > %(cat_bamqc)s;
    scp %(cat_bamqc)s %(localhost)s:%(localdir)s;
    ssh %(localhost)s "source ~/.bash_profile; psql -d sblab -U dberaldi -w < %(upload_script)s"
    ' &> /dev/null
""" %{'bamqcdir':BAMQCDIR.rstrip('/'), 'cat_bamqc': os.path.join(BAMQCDIR, 'bamqc.tsv'), 'localhost':LOCALHOST, 'localdir': LOCALDIR, 'bamqc_local': os.path.join(LOCALDIR, 'bamqc.tsv'), 'upload_script': UPLOAD_SCRIPT}
p= subprocess.Popen(cmd, shell= True)