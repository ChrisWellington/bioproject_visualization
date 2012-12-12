# Extract data from the BioProject database and transform it into a GEXF file.  
# A key feature is the creation of meta-nodes (groups) for each organism.
# Chris Wellington, October, 2012 
import os 
import lib.db_export as db_export
import lib.gexf as gexf

#################################################################
### Assign values to variables ##################################
#################################################################
output_dir          = 'outputs'
gexf_file           = 'BioProject.gexf'           # Output GEXF filename 

db_dir              = 'bioproject_files'
db_file             = 'BioProjects.sqlite'     # input SQLite database file 

# Construct paths 
if not os.path.exists(output_dir): os.mkdir(output_dir) # Create the output directory if it does not exist. This step is not done for input files. 
gexf_file_path  = os.path.join(output_dir, gexf_file)   # Path for the output GEXF file 
db_file_path    = os.path.join(db_dir, db_file)         # Input path for the database 


#################################################################
###  Get the data to use for file creation ######################
#################################################################
# use lib.db_export to get the information from the database and NCBI report  
bp_data     = db_export.db_export(db_file_path)
graph_data  = bp_data.run_all()

#################################################################
###  Create the GEXF file  ######################################
#################################################################
# use lib.gexf to create the GEXF file 
gexf_output = gexf.gexf_create(gexf_file_path, 
                                        graph_data['attributes_genome'], 
                                        graph_data['attributes_bp'],
                                        graph_data['hierarchy_genome'],
                                        graph_data['edges'],
                                        graph_data['data_stats_cols'])

# Push information to the GEXF XML object 
gexf_output.prepare_gexf()
gexf_output.add_hierarchy()
gexf_output.add_edges()

# Write out information 
gexf_output.write_out()
