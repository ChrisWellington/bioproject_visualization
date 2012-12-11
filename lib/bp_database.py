# Python module to manage the BioProject database. 
# Chris Wellington, August 15, 2012
import threading        # Items are saved via a daemon thread 
import sqlite3          # Database support
import csv              # Parse NCBI summary and/or the list of BPs to download  
import logging 
from sqlalchemy import Table, Column, Integer, String, Numeric, MetaData, ForeignKey, create_engine, select 
# Note on SQLAlchemy: we work directly with the SQLAlchemy core and _not_ the Object Relational Mapper (ORM). 

logger = logging.getLogger(__name__)


# Launch and operate the SQLite database 
class init_db:
    def __init__(self, db_file, bp_list_file=None, queue_result=None):
        
        self._db_file = db_file # Make avaialble for the saving thread 

        logger.debug("Initializing database; connecting to run queries.")

        #  Initialize the database itself 
        self._engine = create_engine('sqlite:///' + db_file, echo=False)
        self._metadata = MetaData()
        self._tbl_node = Table('tbl_node', self._metadata,
                Column('bp_id', Integer, primary_key=True),
                Column('genome_id', Integer),
                Column('create_date', String), 
                Column('accno', String),
                Column('name', String),
                Column('title', String),
                Column('project_type', String),
                Column('target_capture', String),
                Column('target_material', String),
                Column('target_sample_scope', String),
                Column('organism_name', String),
                Column('organism_supergroup', String),
                Column('method', String),
                Column('data_type', String),
                )
        self._tbl_link = Table('tbl_link', self._metadata,
                Column('id_tbl_link', Integer, primary_key=True),
                Column('id_from', Integer), 
                Column('id_to', Integer), 
                Column('link_genome_id', String), 
                )
        self._tbl_aggregated_data = Table('tbl_aggregated_data', self._metadata, 
                Column('id_aggregated_data', Integer, primary_key=True),
                Column('bp_id', Integer),
                Column('label', String),
                Column('int_count', Integer),
                Column('str_database', String),
                Column('str_url', String), 
                )
                
        self._tbl_data_stats = Table('tbl_data_stats', self._metadata, 
                Column('id_data_stats', Integer, primary_key=True),
                Column('bp_id', Integer),
                Column('db', String),
                Column('unit', String),
                Column('val', Numeric),
                )
        
        self._tbl_sub_organization = Table('tbl_submission_org', self._metadata,
                Column('id_submission_org', Integer, primary_key=True),
                Column('org_name', String),
                Column('org_type', String),
                Column('org_role', String),
                Column('bp_id', Integer),
                )

        self._metadata.create_all(self._engine) 
        self._conn = self._engine.connect()
        
        
        # Launch thread to save connections. Daemon thread, so it will keep running. 
        t = threading.Thread(target=self.save_returned, args=(queue_result,))
        t.daemon = True
        t.start()
        t.setName('save')

        # Parse the BP report file
        if bp_list_file is not None: self.parse_bp_list_file(bp_list_file) 
        
    ##################################################    
    ### Get Return Values ############################
    ##################################################
    def get_count_existing(self):
        return self._count_existing 
        
    def get_count_to_fetch(self):
        return self._count_to_fetch
    
    def get_ids_to_fetch(self): 
        return self._ids_to_fetch

    # Return *list* of all BioProjects in metadata database 
    def get_ids_existing_list(self):
        return self._bp_ids_existing
    # Return *dictionary* of all BioProjects in metadata database
    def get_ids_existing_dict(self):
        return self._bp_ids_existing_dict
    
    
    ##################################################
    ##################################################
    ##################################################
    def find_existing(self): 
        # Find all BioProject nodes in the database  
        bp_nodes = set() 
        s = select([self._tbl_node.c.bp_id])
        result = self._conn.execute(s)
        for row in result:
            bp_nodes.add(row[0])
        return bp_nodes

    def find_new(self, find_link_up=False, find_link_down=True):
        # Find new non-Genome BioProjects that have not been downloaded in the specified directions (up or down) 
        bp_nodes    = self.find_existing()   # All existing BP nodes 
        bp_targets  = set()                 # BioProject targets of the selected direction 
        s = select([self._tbl_link.c.id_from, self._tbl_link.c.id_to], self._tbl_link.c.link_genome_id == None)
        result = self._conn.execute(s)
        for row in result: 
            if find_link_down:  bp_targets.add(row[1])
            if find_link_up:    bp_targets.add(row[0]) 
        
        for id in self._bp_ids_top: bp_targets.add(id)      # Add the top-level nodes from the initial seed file 
        ids_to_fetch = bp_targets.difference(bp_nodes)      # Use set notation to find the difference between what we have and what we want.  
        
        self._ids_to_fetch   = ids_to_fetch 
        self._count_to_fetch = len(ids_to_fetch)
        self._count_existing = len(bp_nodes) 
        


    def get_genome_ids(self): 
        # Find all Genome IDs that are included as source or target nodes on edges  
        tbl_link = self._tbl_link # We reference it several times, so shorten the name 
        downloaded_projects_set = set() 
        result = []
        
        s = select([tbl_link.c.link_genome_id], tbl_link.c.link_genome_id != None,).distinct()

        genome_ids = self._conn.execute(s)
        
        s = select([self._tbl_node.c.bp_id])
        downloaded_projects = self._conn.execute(s)
        
        for item in downloaded_projects: downloaded_projects_set.add(item[0]) # Make a unique set of all BP IDs we have. 
        # Review each genome_id. If it is not saved, add it to the queue in the form of a list (genome_id, BioProject_id)
        for g_id in genome_ids:
            if g_id[0] not in downloaded_projects_set: result.append(g_id[0])
        return result 


    def close_db_connection(self):
        self._conn.close()


    ############################################################
    ## Text processing #########################################
    ############################################################
    # Parse the BioProject summary file, getting all BP ids    
    def parse_bp_report_file(self, _report_file):
        _separator = ","
        _column    = 0
    
        # Read in the report file, pull out bp_ids_all  (report file requires BP IDs - Accession numbers are ignored) 
        _bp_ids_unique = set()
        with file(_report_file, 'rb') as _file_obj:
            for _line in csv.reader(_file_obj, delimiter=_separator, skipinitialspace=True):
                try:
                    _col=_line[_column]
                    _bp_id=_col[5:]
                    _bp_ids_unique.add(int(_bp_id))
                except Exception as e:
                    logger.info("Value not saved as BP ID. Probably header row. Error: %s", e)
        self._bp_ids_all = list(_bp_ids_unique)
    
    def parse_bp_list_file(self, bp_id_file):
        separator = ","
        column    = 0
    
        # Read in the report file, pull out bp_ids_all    
        bp_ids_unique = set()
        with file(bp_id_file, 'rb') as file_obj:
            for line in csv.reader(file_obj, delimiter=separator, skipinitialspace=True):
                try:
                    bp_id = line[column]
                    bp_ids_unique.add(int(bp_id))
                except Exception as e:
                    logger.info("Value not saved as BP ID. Probably header row. Error: %s", e)
        self._bp_ids_top = list(bp_ids_unique)

    def save_returned(self, queue_result):
        # Continue to pull results from the queue when they appear and to save them
        logger.info("Thread to save values created")
        
        engine = create_engine('sqlite:///' + self._db_file, echo=False)
        metadata = MetaData(); metadata.reflect(engine)

        # Connect to tables 
        tbl_node                = Table("tbl_node", metadata, autoload=True)
        tbl_link                = Table("tbl_link", metadata, autoload=True)
        tbl_aggregated_data     = Table("tbl_aggregated_data", metadata, autoload=True)
        tbl_data_stats          = Table("tbl_data_stats", metadata, autoload=True)
        tbl_sub_organization    = Table("tbl_submission_org", metadata, autoload=True)
        conn = engine.connect()
        
        # Insert connections 
        node_ins      = tbl_node.insert()
        link_ins      = tbl_link.insert()
        aggr_ins      = tbl_aggregated_data.insert()
        stats_ins     = tbl_data_stats.insert()
        org_ins       = tbl_sub_organization.insert()

        while True:
            returned_data = queue_result.get()
            returned_status = [0]*5
            returned_items = ["Attributes", "Links", "Aggregated data", "Data stats", "Submission orgs"]

            # Assign "atts", "links", "submission_org", data_stats", and "aggregated_data"
            try: atts = returned_data['bp_nodes']
            except: atts = None  
            
            try: links = returned_data['links']
            except: links = None  
            
            try: submission_org  = returned_data['submission_org']
            except: submission_org = None
            
            try: data_stats = returned_data['data_stats']
            except: data_stats = None 
            
            try: aggregated_data = returned_data['aggregated_data']
            except: aggregated_data = None

            # Collect attributes for each and load to database if there are data to be fetched 
            if ( ( atts is not None )               and ( len(atts) > 0 ) ):             
                logger.debug('Atts: {0}'.format(atts))
                conn.execute(node_ins,     atts)
            if ( ( links is not None )              and ( len(links) > 0 ) ):            
                logger.debug('Links: {0}'.format(links))
                conn.execute(link_ins,     links)
            if ( ( aggregated_data is not None )    and ( len(aggregated_data) > 0 ) ):  
                logger.debug('Aggregated_data: {0}'.format(aggregated_data))
                conn.execute(aggr_ins,     aggregated_data)    
            if ( ( data_stats is not None )         and ( len(data_stats) > 0 ) ):       
                logger.debug('Data_stats: {0}'.format(data_stats))
                conn.execute(stats_ins,    data_stats)    
            if ( ( submission_org is not None )     and ( len(submission_org) > 0 ) ):   
                logger.debug('Submission_org: {0}'.format(submission_org))
                conn.execute(org_ins,      submission_org)

            # Signal that the queue item was processed 
            queue_result.task_done()


       
