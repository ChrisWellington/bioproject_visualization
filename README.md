# bioproject_visualization

Visualize projects and associated metadata in NCBI's BioProject database. 

This set of Python scripts starts with a list of BioProject IDs and downloads those projects along with all related projects (parents and children). The data are stored in an SQlite database and then can be exported into either a simple CSV table or, more powerfully, into a [GEXF](http://gexf.net/format/) file. This file can be opened and edited via [Gephi](http://gephi.org/). 

## Workflow: 

This is an example workflow. 

1. List the seed projects in "bioproject_files/top-level_bps.csv"
    * The projects are listed by ID, not Accession number. The ID is all digits. 
    * The projects listed will be fetched, along with all parent projects and all child projects. 
2. Download the data: `python download_data.py`
3. Export the GEXF file: `python make_gexf.py`
4. Open the resulting GEXF file in "outputs/" using Gephi
5. Run Force Atlas 2 on the resulting network to identify independent sub-networks. Move each independent network to its own page for clarity. 
6. Use "Partition" to color nodes by metadata (such as data type). 
7. Use "Ranking" to set node size proportionally to data volume. 
8. Re-run a layout algorithm on the formatted nodes. 

Further visualization can be done in a web browser with any of a number of GEXF viewers. To use these viewers, export the Gephi files back into GEXF format and then use a tool to display the GEXF file in a browser. My favorite at the moment is [Sigma.js](http://sigmajs.org/). 
