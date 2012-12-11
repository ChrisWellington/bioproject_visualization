# Use NCBI's Eutils for bulk operations 
# Chris Wellington, October 2012

import threading            # Run multiple downloads. Multithreading not needed since downloads are the main time sink. 
import Queue                # Pass tasks between threads 
import time                 # Manage the number of downloads per second 
import urllib3              # Download files from NCBI 
import logging              # Log progress 

import eutils_parser        # Parsers for eutils data  
import eutils               # Enables use of the regulate_rate class 

logger = logging.getLogger(__name__)

def combine_ids(id_list, group_size):
    """Split a list of IDs into strings of the appropiate size, ready to search. Return a queue of the search IDs."""
    total_items = len(id_list)
    gp = []; output = Queue.Queue()     # Queue is used to be thread-friendly 
    i = 0 
    for item in id_list:
        i += 1
        gp.append(item)
        if ( (len(gp) >= group_size) or (i == total_items)): 
            output.put(','.join(map(str, gp)))      # Combine all ids with commas between them but no spaces.
            del gp[:]                               # Delete all elements from the list, but not the list itself 
    return output
    
class regulate_rate:
    """Regulate the rate of hits to the NCBI web server. Intended for use with Eutilities."""
    def __init__(self, min_gap=0.34):
        self._min_gap               = min_gap           # Amount of time between hits. Default is a third of a second. 
        self._last_hit_time         = time.time()       # Track the last hit time 
        self._last_hit_time_lock    = threading.Lock()  # Lock to maintain consistency  
    
    def check_rate(self):
        """Sleep if necessary so that we do not send queries too quickly to NCBI."""
        self._last_hit_time_lock.acquire()              # Acquire the lock so that multiple threads do not conflict 
        time_gap = time.time() - self._last_hit_time    # Find the amount of time since the last website hit to NCBI
        if time_gap < self._min_gap:                    # If the time gap was less than the minimum set...
            time.sleep(self._min_gap - time_gap)        # Sleep at least until min_time has passed 
            logger.info('Sleep triggered for {sec} seconds'.format(sec=self._min_gap - time_gap))
        self._last_hit_time = time.time()               # Update the last hit time to now. 
        self._last_hit_time_lock.release()              # Release the lock so the next thread can start. 
        
    def get_last_hit_time(self):
        """Return the last_hit_time. Should not typically be needed."""
        return self._last_hit_time

class eutils_download():
    def __init__(self, tool='efetch', db='bioproject', group_size=1, max_connections=10, max_threads=10, email='chris.wellington@nih.gov', tool_id='threaded_downloader', **kwargs):
        self._db                    = db                        # Database being queried 
        self._tool                  = tool                      # Tool being used 
        self._group_size            = group_size                # Number of ids to download at once.
        self._max_threads           = max_threads               # Maximum number of threads to spawn. Does not control maximum number of urllib connections. 
        self._kwargs                = kwargs                    # Individual tools can have specific paramaters 

        # urllib3 connection pool for more efficient downloads 
        pool_headers    = {'accept-encoding':'gzip,deflate', 'connection':'keep-alive'}
        self._pool      = urllib3.connectionpool.connection_from_url('http://eutils.ncbi.nlm.nih.gov', timeout=60, maxsize=max_connections, block=True, headers=pool_headers)
        
        # Parameters to be sent to NCBI in all requests (ids being requested are added later) 
        self._url_fields = {'db':db, 'email':email, 'tool':tool_id}

    

    #############################################
    ###  Run Operations  ########################
    #############################################
    
    def threaded_download(self, id_list, queue_result, parse=True, get_links_down=True, get_links_up=True, **kwargs): 
        """Perform a high-level download, starting from a list of IDs"""
        regulate_rate   = eutils.regulate_rate()                    # Regulate the rate of hits to NCBI 
        queue_search    = combine_ids(id_list, self._group_size)    # Generate the queue of search strings.
        self._kwargs.update(kwargs)                                 # Add any keyword arguments received here to the earlier string (overwrite if pre-existing) 

        # Run the download threads 
        thread_names = []       # Track the threads created here so they can be joined.
        for i in range(self._max_threads):
            thr_name = 'bp-' + str(i)
            logger.info('Thread being launched to do efetch. Name: {0}'.format(thr_name))
            t = threading.Thread(
                target=self.manage_download_queue, 
                args=(queue_search, queue_result, get_links_down, get_links_up, regulate_rate, parse, self._kwargs))
            t.start()
            t.name = thr_name
            thread_names.append(thr_name) # List of the names of the threads we want to join at the end of this cycle 
        
        # Wait for all downloads to complete before moving on 
        logger.info("All efetch threads launched; waiting to join threads now.")
        main_thread = threading.currentThread()
        for t in threading.enumerate():
            if t.name in thread_names: 
                logger.debug("Download thread being joined: %s", t.name) 
                t.join()
        logger.info("Current round of efetch completed and all download threads joined.")


    def manage_download_queue(self, queue_search, queue_result, capture_links_down, capture_links_up, regulate_rate, parse, kwargs):
        """Manage multiple low-level downloads, using queues to identify work to be done and results collected."""
        if parse: parser = eutils_parser.parser(db=self._db, tool=self._tool) 
        
        while not queue_search.empty():
            search_string = queue_search.get()          # Get the search string from the queue 
            regulate_rate.check_rate()                  # Prevent too many hits per second to NCBI 
            xml_string = self.download(search_string, **kwargs)   # Download the XML from NCBI 
            if xml_string is not None:
                if parse:   final_result = parser.parse(xml_string, capture_links_down=capture_links_down, capture_links_up=capture_links_up) 
                else:       final_result = xml_string 
                queue_result.put(final_result)
            
            queue_search.task_done() # Signal that queue item is completed  
        
        return  # Only triggered once the queue is empty 

    
    def download(self, search_string, **kwargs):
        """Perform a low-level Efetch download."""
        url_fields       = self._url_fields.copy()      # Create a copy because it will be modified 
        url_fields.update(kwargs)                       # Add any other keyword args received 
        url_fields['id'] = search_string                # Prepare the fields to be sent to NCBI 
        logger.debug("Preparing to fetch search string: {0}".format(search_string))
        
        try:
            url_path    = '/entrez/eutils/{tool_name}.fcgi'.format(tool_name=self._tool) # Form the URL 
            url_request = self._pool.request('GET', url_path, url_fields)
            return url_request.data
        except urllib3.exceptions.TimeoutError: logger.warning("Timeout error during download from NCBI. Search string: {0}".format(id_string))
        
        return None # Only triggered on exception 
