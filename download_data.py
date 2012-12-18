# Download a defined list of BioProjects.
# December, 2012. Chris Wellington

import Queue
import logging
import os
import lib.eutils as eutils
import lib.bp_database as bp_database

################################################
###  Preliminary settings  #####################
################################################
# Input and output files 
bp_data_dir         = 'bioproject_files'
bp_list_file        = 'top-level_bps.csv'   # Top-level bioProjects to fetch recursively  
db_file             = 'BioProjects.sqlite'  # SQLite database file 
max_iterations      = 10                                    # Maximum depth for recursion 

# Break if the specified path does not exist 
if not os.path.exists(bp_data_dir): raise SystemExit('Fatal error: The input directory "{0}" does not exist. The directory must exist and must contain a list of starting BP ids.'.format(bp_data_dir))
bp_list_file_path   = os.path.join(bp_data_dir, bp_list_file)       # Input path for the list of BP ids from which we start
db_file_path        = os.path.join(bp_data_dir, db_file)            # Input path for the database 


# Logging settings (user adjustable)
file_loglevel       = 'INFO'    # Logging level for the file being saved 
term_loglevel       = 'ERROR'  # Logging level for the terminal display 
logfile             = 'primary.log' # Logging file 

# Prepare logging: Log to file and to terminal 
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(logfile);  fh.setLevel(getattr(logging, file_loglevel))
ch = logging.StreamHandler();       ch.setLevel(getattr(logging, term_loglevel))

ch_format = logging.Formatter(fmt='%(name)-15s: %(levelname)-8s %(threadName)-10s %(message)s')
fh_format = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(threadName)-10s %(name)-15s: %(message)s', datefmt='%m-%d %H:%M:%S')
fh.setFormatter(fh_format); logger.addHandler(fh);
ch.setFormatter(ch_format); logger.addHandler(ch);
logger.info('#####-----  Program to download a defined list of BioProjects launched  -----#####')

# Instantiate objects 
queue_result    = Queue.Queue()                                             # Results returned from efetch operations 
bp_db           = bp_database.init_db(db_file_path, bp_list_file_path, queue_result)          # The database being used to save data 
efetch_bp       = eutils.eutils_download(db='bioproject', tool='efetch',   group_size=2,  max_threads=10, max_connections=20)
esummary_genome = eutils.eutils_download(db='genome',     tool='esummary', group_size=50, max_threads=2,  max_connections=5)

################################################
###  Begin operations  #########################
################################################

# BioProject: Get IDs "below" (the "to" end of "from -> to" links) all current IDs 
logger.info('Preparing to download BPs that are *below* the other IDs we fetched') 
i = 0; count_to_fetch = 1; # Declare "while" conditions before the loop 
while ( (count_to_fetch > 0) and (i <= max_iterations) ): 
    logger.debug('Fetching BPs below. Current iteration number %s',i) 
    i = i + 1                                               # Increment the iteration count 
    bp_db.find_new(find_link_up=False, find_link_down=True) # Get the list of IDs that need to be fetched. 
    count_existing  = bp_db.get_count_existing()            # The number of individual IDs already in the database 
    count_to_fetch  = bp_db.get_count_to_fetch()            # The number of individual IDs to fetch. Used for flow control of the "while" loop. 
    ids_to_fetch    = bp_db.get_ids_to_fetch()              # The actual ids to fetch 
    logger.info('Downloaded BPs: {0};\tTo download: {1}'.format(count_existing, count_to_fetch))

    efetch_bp.threaded_download(ids_to_fetch, queue_result) # Add each search string to the queue 
    queue_result.join()        # Wait for all results to be saved before next iteration 

    
# BioProject: Get IDs "above" (the "from" end of "from -> to" links) all current IDs 
logger.info('Preparing to download BPs that are *above* the other IDs we fetched') 
i = 0; count_to_fetch = 1; # Declare "while" conditions before the loop 
while ( (count_to_fetch > 0) and (i <= max_iterations) ): 
    logger.debug('Fetching BPs above. Current iteration number %s',i) 
    i = i + 1                                           # Increment the iteration count 
    bp_db.find_new(find_link_up=True, find_link_down=False)                   # Get the list of IDs that need to be fetched. 
    count_existing  = bp_db.get_count_existing()        # The number of individual IDs already in the database 
    count_to_fetch  = bp_db.get_count_to_fetch()        # The number of individual IDs to fetch. Used for flow control of the "while" loop. 
    ids_to_fetch    = bp_db.get_ids_to_fetch()          # The actual IDs to fetch
    logger.info('Downloaded BPs: {0};\tTo download: {1}'.format(count_existing, count_to_fetch))
    
    efetch_bp.threaded_download(ids_to_fetch, queue_result, capture_links_down=False) # Add each search string to the queue 
    queue_result.join()        # Wait for all results to be saved before next iteration 
    
# Genome: these nodes represent organism overview pages, but have been moved into their own database and must be handled separately. 
genome_ids = bp_db.get_genome_ids()                 # From the database, get a list of genome_ids 
esummary_genome.threaded_download(genome_ids, queue_result)  # Fetch and parse the associated files 

# Wait until all results have been saved 
queue_result.join() # Wait until everything has been saved 
