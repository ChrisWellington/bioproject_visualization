# Parse XML returned from NCBI Eutilities  
# Chris Wellington, September 2012

import xml.etree.cElementTree as ET  # Parse XML 
import logging
import datetime

logger = logging.getLogger(__name__)

class parser:
    def __init__(self, db='bioproject', tool='efetch'):
        self._db    = db    # Database being queried 
        self._tool  = tool  # Tool being used 
        logger.debug("Parser instantiated with database: {database} and with tool: {tool}".format(database=db, tool=tool))

    def parse(self, xml_string, **kwargs):
        """Set up the correct parser."""
        if self._db == 'bioproject':   
            if self._tool == 'efetch':      return self.parse_efetch_bioproject(xml_string, **kwargs)
        elif self._db == 'genome':
            if self._tool == 'esummary':    return self.parse_esummary_genome(xml_string, **kwargs)

        # If we reach this far without triggering "return", we know that the parser was not found. 
        logger.critical('No parser provided for the given combination of tool and database. Tool: {tool}, Database: {database}'.format(tool=self._tool, database=self._db))
    
    def parse_esummary_genome(self, xml_string, **kwargs):
        genome_tbl  = [] 
        # Wrap parsing into a 'try...except' loop to catch errors 
        try:
            xml_tree = ET.fromstring(xml_string)
        except Exception as e:
            logger.warning("Error parsing genome results. Error report: \n%s", e)
        
        for sub_el in xml_tree:
            if sub_el.tag == "DocSum":
                tmp_dict = {}
                for DocSum_sub in sub_el:
                    if DocSum_sub.tag == "Id":      genome_id = DocSum_sub.text
                    if DocSum_sub.tag == "Item":    tmp_dict[DocSum_sub.attrib.get("Name")] = DocSum_sub.text
                                    
                # Add to the table of Genome records. Simple structure and everything is 1:1 mapping. 
                genome_tbl.append({
                    'bp_id':tmp_dict["ProjectID"], 'genome_id':genome_id, 
                    'name':tmp_dict["Organism_Name"], 
                    'title':tmp_dict["Organism_Name"],
                    'organism_supergroup':tmp_dict["Organism_Kingdom"], 
                    'organism_name':tmp_dict["Organism_Name"], 
                    'project_type':'Organism Overview' }) 
        
        # Return a dictionary with a single key:value pair 
        return {'bp_nodes':genome_tbl, 'links':None, 'data_stats':None, 'submission_org':None, 'aggregated_data':None}
    
    
    def parse_efetch_bioproject(self, xml_string, capture_links_down=True, capture_links_up=True, **kwargs):
        logger.debug("Parsing bioProject")
        
        # Data lists (each element will be a dictionary and will correspond to one row)
        bp_nodes            = []   # List of BioProject nodes (each node is a dictionary) 
        links               = []   # List of links (each link is a list: [from, to, other info] )
        aggregated_data     = []   # Aggregated Data section from BioProjects.
        data_stats          = []   # Data statistics 
        submission_org      = []   # Submission Organizations.

        
        # Fields that will serve as the columns in the SQL tables. Used to populate dictionaries. 
        bp_nodes_fields = [
                'bp_id', 'genome_id', 'create_date', 'accno', 'name', 'title', 'project_type', 'target_capture', 'target_material',
                'target_sample_scope', 'organism_name', 'organism_supergroup', 'method', 'data_type',]
        link_fields              = ['id_from', 'id_to', 'link_genome_id']
        aggregated_data_fields   = ['bp_id', 'label', 'int_count', 'str_database', 'str_url']
        data_stats_fields        = ['bp_id', 'db', 'unit', 'val'] 
        sub_organization_fields  = ['org_name', 'org_type', 'org_role', 'bp_id']


        # Parsing is wrapped in a "try" statement. There should not be errors here.
        i = 0
        try:
            xml_tree = ET.fromstring(xml_string)
        except Exception as e: 
            logger.warning('Error parsing BioProject XML')
            return None # This avoids running the post-parsing steps and sends something back to the calling function. 
        # For each DocumentSummary
        for DocSum_tag in xml_tree.findall('DocumentSummary'):
            bp_atts = dict.fromkeys(bp_nodes_fields) # Create a dictionary of attributes to be captured

            try: # Wrap the entire Document Summary extraction in a try statement to catch errors
                # Iterate through top-level nodes under DocSum, almost stream-style 
                bp_atts['bp_id'] = DocSum_tag.find('Project/ProjectID/ArchiveID').attrib["id"] # Get ProjectID 
                for sub_el in DocSum_tag:
                    # Project Information 
                    if sub_el.tag == "Project":
                        bp_atts['accno']            = sub_el.find('ProjectID/ArchiveID').attrib.get("accession") 
                        bp_atts['name']             = sub_el.findtext('ProjectDescr/Name')
                        bp_atts['title']            = sub_el.findtext('ProjectDescr/Title')
                        bp_atts['organism_name']    = sub_el.findtext('ProjectType/*Target/Organism/OrganismName')
                        
                        catch_errors = [
                            "bp_atts['project_type']        = sub_el.find('ProjectType/*').tag[11:]",
                            "bp_atts['target_capture']      = sub_el.find('ProjectType/*/Target').attrib.get('capture')[1:]",
                            "bp_atts['target_material']     = sub_el.find('ProjectType/*/Target').attrib.get('material')[1:]",
                            "bp_atts['target_sample_scope'] = sub_el.find('ProjectType/*/Target').attrib.get('sample_scope')[1:]",
                            "bp_atts['genome_id']           = sub_el.find('ProjectType/*Target/Organism').attrib.get('species')",
                            "bp_atts['organism_supergroup'] = sub_el.find('ProjectType/*Target/Organism/Supergroup').text[1:]",
                            "bp_atts['method']              = sub_el.find('ProjectType/*/Method').attrib.get('method_type')[1:]",
                            "bp_atts['data_type']           = sub_el.find('ProjectType/*/Objectives/Data').attrib.get('data_type')[1:]",]
                        for c in catch_errors: # Should the "exec" be compiled? Is the exec even a good idea? 
                            try: exec c
                            except: pass

                        p_type = sub_el.find('ProjectType/*') 
                        if p_type is not None:
                            if p_type.attrib.get('subtype') == 'eAuthorizedAccess':
                                bp_atts['project_type'] = 'TopAdmin: Authorized Access'

                    # Relation Set information (edges in the graph)
                    elif sub_el.tag == "RelationSet":
                        for RelationGroup in sub_el.findall('RelationGroup'):  # Only capture RelationGroup tags (summary tags can be present) 
                            rg_level = RelationGroup.attrib.get('level')
                            if rg_level == 'same': continue # Do not parse if the level is "same" 
                            
                            for RelationData in RelationGroup.findall('RelationData'):
                                link_atts = dict.fromkeys(link_fields) # Initialize, adding each key (null values)
                                bp_target = RelationData.get('id') # The other project involved; could be source or target
                                
                                try:    link_atts['link_genome_id'] = RelationData.find('GenomeID').text  
                                except: pass 
                                
                                # Get the order right for relationships (the "from" --> "to" part) 
                                if ( ( rg_level == 'Up' ) and ( capture_links_up ) ):
                                    link_atts['id_from'] = bp_target
                                    link_atts['id_to']   = bp_atts['bp_id']
                                    links.append(link_atts)
                                elif ( ( rg_level == 'Down' ) and ( capture_links_down ) ):  
                                    link_atts['id_from'] = bp_atts['bp_id']
                                    link_atts['id_to']   = bp_target
                                    links.append(link_atts)

                                # Add to the list of links

                    # Aggregated Data Sets: Create dictionary and add to list 
                    elif sub_el.tag == "AggregatedDataSet":
                        for data_gp in sub_el:
                            if data_gp.tag != 'AggregatedData': continue
                            aggregated_data_atts = dict.fromkeys(aggregated_data_fields)
                            aggregated_data_atts['bp_id']        = bp_atts['bp_id']
                            aggregated_data_atts['label']        = data_gp.attrib.get('label') 
                            aggregated_data_atts['int_count']    = data_gp.attrib.get('count')
                            aggregated_data_atts['str_database'] = data_gp.find('DB').text
                            aggregated_data_atts['str_url']      = data_gp.find('URL').text
                            aggregated_data.append(aggregated_data_atts)
                    # Submission / Submitter Information 
                    elif sub_el.tag == "Submission":
                        for sub_gp in sub_el.findall('Organization'):
                            sub_atts = dict.fromkeys(sub_organization_fields)
                            try: 
                                sub_atts['bp_id']       = bp_atts['bp_id']
                                sub_atts['org_name']    = sub_gp.attrib.get('role')
                                sub_atts['org_type']    = sub_gp.attrib.get('type')
                                sub_atts['org_role']    = sub_gp.find('Name').text
                                submission_org.append(sub_atts)
                            except Exception as e:
                                logger.info("Failed to process submitter string. BioProject: %s; error report: \n%s", bp_atts['bp_id'], e)
                    # Data Statistics
                    elif sub_el.tag == 'DataStatistics': 
                        for data_gp in sub_el.findall('Data'):
                            if bp_atts['project_type'] == 'TopAdmin: Authorized Access': continue # If this is an Authorized Access project, do not capture statistics 
                            data_stats_atts = dict.fromkeys(data_stats_fields)
                            data_stats_atts['bp_id']     = bp_atts['bp_id']
                            data_stats_atts['db']        = data_gp.attrib.get('db')
                            data_stats_atts['unit']      = data_gp.attrib.get('unit')
                            data_stats_atts['val']       = data_gp.text.replace(',','') # Remove commas

                            # Standardize SRA units to Gigabases and Terabytes 
                            if data_stats_atts['db'] == 'SRA':
                                if data_stats_atts['unit'] == 'Mbases':
                                    try:
                                        data_stats_atts['val']       = ( float(data_stats_atts['val']) / 1000 )
                                        data_stats_atts['unit']      = 'Gbases'
                                    except: logger.info("Error in converting megabases to gigabases")
                                elif data_stats_atts['unit'] == 'Mbytes':
                                    try:
                                        data_stats_atts['val']       = ( float(data_stats_atts['val']) / 1000000 )
                                        data_stats_atts['unit']      = 'Tbytes'
                                    except Exception as e: logger.info("Error in converting megabytes to Terabytes, %s", e)
                                    

                            data_stats.append(data_stats_atts)
                    # Creation date, most common date in document 
                    elif sub_el.tag == "CreateDate":
                        try:    
                            date = datetime.datetime.strptime(sub_el.text,'%d-%b-%Y')
                            bp_atts['create_date'] = date.strftime("%Y-%m-%d") 
                        except Exception as e:
                            logger.info("Failed to get and parse the CreateDate. BioProject: %s; error report: \n%s", bp_atts['bp_id'], e)
                    else: pass 
                # Push most recent dictionary of values to list, adding one row of data 
                bp_nodes.append(bp_atts)
                i =+ 1
            # If DocumentSummary fails 
            except Exception as e: 
                logger.warning('Failed to parse individual Document Summary')
                logger.debug("DocSum error report: \n\t%s", e)
        if i == 0:
            logger.warning('No DocSum parsed from current document.')
            logger.debug('XML from which no DocSum was parsed: \n%s', xml_string)
        
        return {'bp_nodes':bp_nodes, 'links':links, 'data_stats':data_stats, 'submission_org':submission_org, 'aggregated_data':aggregated_data}
        
