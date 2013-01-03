# Visualization Demo

This set of files demonstrates the process of visualizing BioProject data in a web browser.

The general process is relatively straightforward: 

* BioProject data are downloaded from NCBI and parsed into an SQLite database (`download_data.py`). 
* Data are exported from the SQLite database to a [GEXF](http://gexf.net/format/) graph file (`make_gexf.py`). 
* The GEXF file is loaded into [Gephi](http://gephi.org/) for node layout, labeling, and coloring.
* The resulting graphs are exported in GEXF format where they can be visualized in a web browser (the point of this demo). 

For this demo, Steps 1, 2, and 3 have already been completed. The first two can be done following instructions for the main package. The third step requires manual intervention to decide how you want the layout to look and what metadata you want to emphasize in the finished graph. In these examples, the nodes were colored according to data type and were sized according to the number of bases of sequence data in SRA. I tried to avoid manually adjusting the layout after running layout algorithms (mostly Force Atlas 2 or Parallel Force Atlas). 

## In-browser visualization 

Though it is possible to interact with graphs in Gephi, this requires users to install and learn a dedicated software package. The goal of providing in-browser visualization is to reduce the barrier for users interested in interacting with the graphs. It also provides the opportunity to customize the display of node metadata, making it easier to find important information. 

There are numerous tools to achieve this, but in this example I am using [Sigma.js](http://sigmajs.org/). This is an open-source Javascript library that loads and displays GEXF files in a web browser (Firefox works best in my experience). I have added numerous additional Javascript functions that enable the user to interact dynamically with the graph, adjusting options and the like. 

## Running the demo 

To run the demo, save all of the files (and directories) in this directory to your computer. Open the index.html file in a web browser, preferably Firefox (Chrome's default security settings do not allow code to run when saved to your local hard disk and I have been unable to get Internet Explorer to work). You should be presented with a graph display if everything works. If so, you can scroll around, change the size of nodes, and make other adjustments. None of the changes you make are being made to the underlying GEXF file, they are only being applied to your particular display. 

