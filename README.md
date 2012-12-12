bioproject_visualization
========================

Visualize projects and associated metadata in NCBI's BioProject database. 

Workflow: 
1) List the top-level IDs to be fetched (they and everything under them will be fetched) in "bioproject_files/top-level_bps.csv"
2) Run download_data.py (python download_data.py) 
3) Run make_gexf.py (python make_gexf.py)
4) Open the resulting GEXF file in outputs/ (using Gephi)
