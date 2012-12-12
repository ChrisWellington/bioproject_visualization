# Extract data from the BioProject database and transform it into a simple table.
# Chris Wellington, August 28, 2012 
import os 
import lib.db_export as db_export
import csv
import codecs
import cStringIO

#################################################################
### Assign values to variables ##################################
#################################################################
output_dir          = 'outputs'
table_file          = 'BioProject-table.csv'           # Output GEXF filename 

db_dir              = 'bioproject_files'
db_file             = 'BioProjects.sqlite'     # input SQLite database file 

if not os.path.exists(output_dir): os.mkdir(output_dir) # Create the output directory if it does not exist. This step is not done for input files. 

table_file_path  = os.path.join(output_dir, table_file)   # Path for the output GEXF file 
db_file_path    = os.path.join(db_dir, db_file)         # Input path for the database 

#################################################################
###  Get the data to use for file creation ######################
#################################################################
# use lib.db_export to get the information from the database and NCBI report  
bp_data     = db_export.db_export(db_file_path)
graph_data  = bp_data.run_all()

# Make the ordered list of fields to keep. 
tbl_fields = ['bp_id', 'create_date', 'accno', 'name', 'title', 'project_type', 'target_capture', 'target_material', 'organism_name', 'organism_supergroup', 'method', 'data_type']
tbl_fields.extend(graph_data['data_stats_cols'])

# Copy the list to a dictionary 
tbl_fields_dict = {}
i = 0
for element in tbl_fields:
    tbl_fields_dict[element] = i
    i = i + 1

data_table = []
data_table.append(tbl_fields)

for bp_id, value_dict in graph_data['attributes_bp'].items():
    tmp_row = [""]*len(tbl_fields)
    tmp_row[0] = unicode(bp_id)
    for col, val in value_dict.items():
        if col in tbl_fields_dict:
            tmp_row[tbl_fields_dict[col]] = unicode(val)
    data_table.append(tmp_row) 


            
class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)



with open(table_file_path, 'wb') as f:
    #writer = csv.writer(f)
    writer = UnicodeWriter(f)
    writer.writerows(data_table)
