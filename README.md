# bioproject_visualization

Visualize projects and associated metadata in NCBI's BioProject database. 

## Workflow: 
This is an example simple workflow. 
* List the top-level IDs to be fetched (they and everything under them will be fetched) in "bioproject_files/top-level_bps.csv"
* Run download_data.py (python download_data.py) 
* Run make_gexf.py (python make_gexf.py)
* Open the resulting GEXF file in outputs/ (using Gephi)
