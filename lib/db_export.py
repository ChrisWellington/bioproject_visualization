# This module pulls values from the bp database so that it can be used when running exports.  
# Chris Wellington, Aug 7, 2012 

import csv                              # Parse CSV input file (NCBI data report)
import datetime                         # Work with dates 
import dateutil.relativedelta           # Add one month to the final date in the  time series 
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, create_engine, select 
from collections import defaultdict     # Quick way to get a dictionary of lists

class db_export:
    "Provide access to bioproject data for various exporters"
    ####  Variables used within the class ####
        # _atts_genome
        # _atts_bp 
        # _edges         
    
    ###############################################
    def __init__(self, db_file):
        self._db_file       = db_file           # The database of BioProject data 

    ##########################################################################################
    ##  Return values ########################################################################
    ##########################################################################################
    def get_report_values(self):
        return self._report_values
    
    def get_atts_genome(self):
        return self._atts_genome
        
    def get_atts_bp(self):
        return self._atts_bp
    
    def get_hierarchy_genome(self):
        return self._hierarchy_genome 

    def get_edges(self):
        return self._edges 
        
    
    def run_all(self):
        self.get_db_rows()
        self.parse_genome_hierarchy()
        
        tmp_dict = {}
        #tmp_dict['report_dates']            = self._report_dates
        #tmp_dict['report_values']           = self._report_values
        tmp_dict['attributes_genome']       = self._atts_genome
        tmp_dict['attributes_bp']           = self._atts_bp
        tmp_dict['hierarchy_genome']        = self._hierarchy_genome
        tmp_dict['edges']                   = self._edges
        tmp_dict['data_stats_cols']         = self._data_stats_cols
        
        return tmp_dict 
    
    ##########################################################################################
    ##  Get existing information #############################################################
    ##########################################################################################
    # Fetch data from the database, return everything in dictionaries  
    def get_db_rows(self): 
        # Establish the db connection  
        engine = create_engine('sqlite:///' + self._db_file, echo=False)
        metadata = MetaData(); metadata.reflect(engine)
        tbl_node                = Table("tbl_node",  metadata, autoload=True)
        tbl_stats               = Table("tbl_data_stats", metadata, autoload=True)
        tbl_link                = Table("tbl_link",  metadata, autoload=True)
        conn = engine.connect()

        # Get all unique data_stats, create a dictionary and a set of the column headers 
        unique_cols = set()
        data_stats = defaultdict(dict)
        
        s = select([tbl_stats.c.bp_id, tbl_stats.c.db, tbl_stats.c.unit, tbl_stats.c.val]).distinct()
        for line in conn.execute(s):
            col_header = str(line[1])+": "+str(line[2]) 
            data_stats[str(line[0])][col_header] = line[3]  
            unique_cols.add(col_header)

        
        # Get all genome (organism) nodes and transform to a dictionary 
        atts_genome = {}
        s = select([tbl_node], tbl_node.c.project_type == 'Organism Overview')
        for line in conn.execute(s):
            tmp_hash = {}
            for col in line.keys():
                # The BioProject ID ("ID") will become the new dict key - capture it.  
                if ( col == 'bp_id' ):
                    bp_id = str(line[col])
                elif ( line[col] is not None ):
                    tmp_hash[col] = str(line[col])
            # Append most recent Genome
            atts_genome[bp_id] = tmp_hash

        # Get all non-Genome BioProject nodes and transform into a dictionary 
        atts_bp = {}
        s = select([tbl_node], tbl_node.c.project_type != 'Organism Overview')
        for line in conn.execute(s):
            tmp_hash = {}
            for col in line.keys():
                if (  col == 'bp_id' ):
                    bp_id = str(line[col])
                elif ( line[col] is not None ):
                    tmp_hash[col] = unicode(line[col])
                else: 
                    if line['project_type'] is not None:
                        tmp_hash[col] = unicode(line['project_type'])
                    else: 
                        tmp_hash[col] = None 
            
            if bp_id in data_stats:
                for stat in data_stats[bp_id].keys():
                    tmp_hash[stat] = str(data_stats[bp_id][stat])
                    
            # Append most recent BioProject 
            atts_bp[bp_id] = tmp_hash
            
            
        # Get all edges and transform into a dictionary 
        s = select([tbl_link.c.id_from, tbl_link.c.id_to]).distinct()
        edges = [[str(row[0]), str(row[1])] for row in conn.execute(s)]
        
        # Exports 
        self._atts_genome       = atts_genome
        self._atts_bp           = atts_bp
        self._edges             = edges            
        self._data_stats_cols   = unique_cols 


    # Starting with a table of edges, group BioProjects under Genomes 
    def parse_genome_hierarchy(self):
        hierarchy_genome = defaultdict(set) # Allows appending without checking existence while the set ensures uniqueness.
        # For each line in the table of edges, if "From" is an organism, put the target BioProject under that organism.
        for line in self._edges:  
            if line[0] in self._atts_genome:
                hierarchy_genome[line[0]].add(line[1])
        
        # We have the hierarchy structure. Now we want to add _report_values to the top-level genomes. 
        for genome_id, bp_list in hierarchy_genome.items():
            #tmp_report_dict = defaultdict(dict)   # Dict of dicts 
            tmp_att_dict    = dict()   

            for col in self._data_stats_cols:
                tmp_att_dict[col] = 0 
                for bp_id in bp_list:
                    #try: print "Data found for col " + col + " and bp " + str(bp_id) + ":\t " + str(self._atts_bp[bp_id][col])
                    #except: pass
                    if col in self._atts_bp[bp_id]:
                        try:    tmp_att_dict[col] = tmp_att_dict[col] + float(self._atts_bp[bp_id][col])
                        except: print "Found data but unable to use it. Sorry!"


            # Add the new Genome data to the report_values 
            #self._report_values[genome_id]  = tmp_report_dict 
            self._atts_genome[genome_id].update(tmp_att_dict)
        
        self._hierarchy_genome = hierarchy_genome 
    
    def clean_data_volume(self, data_list):
        returned_list = []
        for x in data_list:
            try:
                float(x)
                returned_list.append(float(x))
            except ValueError:
                returned_list.append(0)
        return returned_list 
