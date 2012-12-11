# This is a module to integrate BioProject data in a database with XML outputs. Uses: 
#   Create a GEXF file for import into Gephi from a database of nodes and edges. 
# For GEXF, this creates meta-nodes for each organism.
# Chris Wellington, Aug 6, 2012 

import xml.etree.cElementTree as ET     # Write out XML
from collections import defaultdict     # Quick way to get a dictionary of lists

# Primary class for assembling XML files
class gexf_create:
    "Create a GEXF graph file to import to Gephi"

    ###############################################
    def __init__(self, filename, g_type, report_dates, report_values, atts_genome, atts_bp, h_genome, edges, data_stats_cols):
        self._g_type            = g_type          # Should be either "static" or "dynamic" 
        self._report_dates      = report_dates
        self._report_values     = report_values 
        self._atts_genome       = atts_genome
        self._atts_bp           = atts_bp
        self._hierarchy_genome  = h_genome
        self._edge_data         = edges
        self._filename          = filename
        self._data_stats_cols   = data_stats_cols


    # Create the framework for the XML (root node), and add the metadata node, nodes node, and edges node 
    def prepare_gexf(self):
        #### Prepare the GEXF XML elements ####
        # Create root element 
        root = ET.Element("gexf")
 
        # Start of the actual graph section. Currently dynamic.
        graph_info = ET.SubElement(root, 'graph', {'defaultedgetype':'directed','mode':self._g_type,'timeformat':'date'})

        # Set the fields avaialble to the nodes. Each field goes into a separate subelement. Field names match those in the database for simplicity.
        node_atts = ET.SubElement(graph_info, 'attributes', {'class':'node', 'type':self._g_type})
        gexf_atts = [
                ('G bases',             'GigaBases',        'float'), 
                ('T bytes',             'TeraBytes',        'float'),
                ('genome_id',           'Genome_id',        'string'),
                ('create_date',         'create_date',      'string'),
                ('accno',               'Accno',            'string'),
                ('title',               'Title',            'string'),
                ('project_type',        'Project_type',     'string'),
                ('target_capture',      'Target_capture',   'string'),
                ('target_material',     'Target_material',  'string'),
                ('target_sample_scope', 'Target_scope',     'string'),
                ('organism_name',       'Organism_name',    'string'),
                ('organism_supergroup', 'Kingdom',          'string'),
                ('method',              'Method',           'string'),
                ('data_type',           'Data_type',        'string')]
        # Add standard fields 
        for field in gexf_atts:
            ET.SubElement(node_atts, 'attribute', {'id':field[0], 'title':field[1], 'type':field[2]})

        # Add the columns that were given from Data Statistics. We do not know these columns until the data are passed in. 
        for col in self._data_stats_cols:
            ET.SubElement(node_atts, 'attribute', {'id':col, 'title':col, 'type':'float'})

        # Set up the containers for the nodes and edges 
        nodes = ET.SubElement(graph_info, 'nodes') # Nodes 
        edges = ET.SubElement(graph_info, 'edges') # Edges 

        # Export what we just did.
        self._nodes     = nodes
        self._edges     = edges
        self._root      = root 
        self._gexf_atts = gexf_atts

    ##########################################################################################
    ##  Begin creating XML nodes  ############################################################
    ##########################################################################################
    def add_hierarchy(self):

        for genome_id, bp_list in self._hierarchy_genome.items():
            # Create the group container node. Parent node is just the top level node container in this case. 
            genome_group_node = self.create_genome_node(genome_id, True)

            # Create the sub-nodes for that group, add the genome node, then add all related bioproject nodes.  
            nested_nodes_container = ET.SubElement(genome_group_node, 'nodes')
            genome_node = self.create_genome_node(genome_id, False) 
            nested_nodes_container.append(genome_node) 

            for bp_id in bp_list:
                try:  nested_nodes_container.append(self.create_bp_node(bp_id))
                except Exception as e:  print "Error adding BioProject data node under the organism. Moving on. ", str(e)
                del self._atts_bp[bp_id]     # This prevents duplicate BioProject nodes 

            # Add to the parent "_nodes" 
            self._nodes.append(genome_group_node) 

        # Add the remaining flat BioProjects
        for bp_id in self._atts_bp:
            self._nodes.append(self.create_bp_node(bp_id))

    def add_edges(self):
        for edge in self._edge_data:
            ET.SubElement(self._edges, 'edge', {'source':edge[0],'target':edge[1]})

    def write_out(self):
        xml_file = open(self._filename,"w")
        ET.ElementTree(self._root).write(xml_file)

    
    ##########################################################################################
    ##  Functions used internally only  ######################################################
    ##########################################################################################
    def create_genome_node(self, bp_id, group): 
        if group: node_atts = { 'label':self._atts_genome[bp_id]['name'], 'id':'group_'+str(bp_id) }
        else:     node_atts = { 'label':self._atts_genome[bp_id]['name'], 'id':str(bp_id) }
    
        genome_node     = ET.Element('node', node_atts)
        attvalues_node  = ET.SubElement(genome_node, 'attvalues') 

        # For every attribute, add an attvalue node 
        for key, value in self._atts_genome[bp_id].items():
            ET.SubElement(attvalues_node, 'attvalue', {'for':key,'value':str(value)})

        # For the other attributes, fill in with "Organism Overview" 
        for att_set in self._gexf_atts:
            if ( ( att_set[0] not in self._atts_genome[bp_id] ) and ( att_set[2] == 'string' ) ):
                ET.SubElement(attvalues_node, 'attvalue', {'for':att_set[0],'value':'Organism Overview'})

        # Make attvalue nodes for all data types in the report. Do static nodes unless specified otherwise.  
        if self._g_type == 'dynamic': 
            i = 0
            for daterange in self._report_dates:
                start_date = daterange[0]
                end_date   = daterange[1]
                
                if bp_id in self._report_values: 
                    for data_type in self._report_values[bp_id]:
                        val = str(self._report_values[bp_id][data_type][i])
                        ET.SubElement(attvalues_node, 'attvalue', 
                                    {'for':data_type, 'value':val, 'start':start_date, 'end':end_date})
                i = i + 1 
        else: 
            if bp_id in self._report_values: 
                for data_type in self._report_values[bp_id]:
                    val = str(self._report_values[bp_id][data_type][-1])
                    ET.SubElement(attvalues_node, 'attvalue', {'for':data_type, 'value':val })
        
        return genome_node 

    # Create a BioProject node (these are not currently used as containers) 
    def create_bp_node(self, bp_id):
        try:    bp_name = self._atts_bp[bp_id]['name']
        except: bp_name = "none"
        
        node_atts       =  {'label':bp_name, 'id':bp_id}
        bp_node         = ET.Element('node', node_atts)
        attvalues_node  = ET.SubElement(bp_node, 'attvalues') 

        # For every attribute, add an attvalue node 
        for key, value in self._atts_bp[bp_id].items():
            ET.SubElement(attvalues_node, 'attvalue', {'for':key,'value':value})
        
        # Make attvalue nodes for all data types in the report. Do static nodes unless specified otherwise.  
        if self._g_type == 'dynamic': 
            i = 0
            for daterange in self._report_dates:
                start_date = daterange[0]
                end_date   = daterange[1]
                
                if bp_id in self._report_values: 
                    for data_type in self._report_values[bp_id]:
                        val = str(self._report_values[bp_id][data_type][i])
                        ET.SubElement(attvalues_node, 'attvalue', {'for':data_type, 'value':val, 'start':start_date, 'end':end_date})
                i = i + 1 
        else: 
            if bp_id in self._report_values: 
                for data_type in self._report_values[bp_id]:
                    val = str(self._report_values[bp_id][data_type][-1])
                    ET.SubElement(attvalues_node, 'attvalue', {'for':data_type, 'value':val })
        return bp_node 
