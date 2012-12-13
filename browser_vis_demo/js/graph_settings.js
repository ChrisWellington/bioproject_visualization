// Instanciate sigma.js outside of functions so it can be called globally 
var sigInst = sigma.init($('#gexf-container')[0]); 
var zoomDelay = 1.1; 

function setGEXF(gexf_file) {
    // Set properties on sigInst (instantiated above) 
    sigInst.drawingProperties({
        defaultLabelColor: '#fff',
        defaultEdgeType: 'curve',
      }).mouseProperties({
        maxRatio:100,
        minRatio:.5 // Enable some, but not too much, zooming out. 
        });
    
    sigInst.parseGexf(gexf_file);   // File being parsed (requires "sigma.parseGexf.js")
    //sigInst.draw();                 // Draw graph 
    }

function bindActions(){
    var popUp;
    
    function numberWithCommas(x) {
            var parts = x.toString().split(".");
            parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
            if (parts[1]==0) { 
                return parts[0];
            } else {
                if (parts[0].length>=3){ 
                    return parts[0];
                } else {
                    return parts.join(".");
                }
            }
        }
    
    function attributesToObject(attr_list) {
        // Combine attributes to a single object (hash-like structure) 
        attrObj = new Object(); 
        attr_list.map( function(nested_attr)  { 
            attrObj[ nested_attr['attr'] ] = nested_attr['val'];
        })
        
        // Create the HTML that will be used when displaying the data 
        var return_text = '<table class="node">' 
        if (  attrObj.hasOwnProperty('title') ) {
            return_text += '<tr><td>Title</td><td>' + attrObj['title'] + '</td></tr>'
        }

        if (  attrObj.hasOwnProperty('SRA: Gbases') || attrObj.hasOwnProperty('SRA: Tbytes') ) { 
            return_text += '<tr><td>SRA</td><td>' // Add title line 
            if (  attrObj.hasOwnProperty('SRA: Gbases') ) { 
                return_text += numberWithCommas(attrObj['SRA: Gbases'])  + ' Gbase; ' 
            }
            if (  attrObj.hasOwnProperty('SRA: Tbytes') ) { 
                return_text += numberWithCommas(attrObj['SRA: Tbytes']) + ' Tbyte'
            }
            return_text += '</td></tr>'
        }
        
        // Get the "Project Type" label and save it to a variable. 
        if (  attrObj.hasOwnProperty('project_type') ) { 
            return_text += '<tr><td>Project type</td><td>' + attrObj['project_type'] + '</td></tr>'
            var project_type = attrObj['project_type'] 
        } else {
            var project_type = "" 
        }
        
        // Remove any attributes that are simply "Other" or that match the Project Type 
        for (var attribute in attrObj) {
            var att_value = attrObj[attribute];
            if ( att_value=='Other' || att_value==project_type ) {
                delete attrObj[attribute]; 
            }
        }
        
        if (  attrObj.hasOwnProperty('method') ) {
            return_text += '<tr><td>Method</td><td>' + attrObj['method'] + '</td></tr>'
        }                
        if (  attrObj.hasOwnProperty('data_type') ) {
            return_text += '<tr><td>Data type</td><td>' + attrObj['data_type'] + '</td></tr>'
        }                

        if ( attrObj.hasOwnProperty('target_capture') || attrObj.hasOwnProperty('target_material') ) {
            return_text += '<tr><td>Target</td><td>'; 
            if ( attrObj.hasOwnProperty('target_material') ) {
                return_text += '<em>material:</em> ' + attrObj['target_material'] + "; ";
            }
            if ( attrObj.hasOwnProperty('target_capture') ) {
                return_text += '<em>capture:</em> ' + attrObj['target_capture'];
            }
            return_text += '</td></tr>';
        }
        return_text += '</table>'
        return return_text 
    }

    function showNodeInfo(event) {
        popUp && popUp.remove();

        var node;
        sigInst.iterNodes(function(n){
            node = n;
        },[event.content[0]]);

        popUp = $(
            '<div class="node-info-popup"></div>'
        ).append(
        // The GEXF parser stores all the attributes in an array named 'attributes'. And since sigma.js does not recognize the key
        // 'attributes' (unlike the keys 'label', 'color', 'size' etc), it stores it in the node 'attr' object :
        attributesToObject( node['attr']['attributes'] )
        ).attr(
            'id',
            'node-info'+sigInst.getID()
        ).css({
            'display': 'inline-block',
            'border-radius': 3,
            'padding': 5,
            'background': '#fff',
            'color': '#000',
            'box-shadow': '0 0 4px #666',
            'position': 'absolute',
            'left': node.displayX,
            'top': node.displayY+15
        });

        $('#gexf-container').append(popUp);
    }

    function hideNodeInfo(event) {
        popUp && popUp.remove();
        popUp = false;
    }
    
    // Open BioProject in new window only when the user releases the mouse button. 
    function unclickNode(event) {
        var bp_id = event.content[0]
        window.open('http://www.ncbi.nlm.nih.gov/bioproject/' + bp_id); 
    }

    sigInst.bind('overnodes',showNodeInfo).bind('outnodes',hideNodeInfo);
    sigInst.bind('upnodes',unclickNode);
}

// Set graph properties 
function setGraphProperties(params) { 
    sigInst.graphProperties(params);
    sigInst.draw();
}

// Set drawing properties 
function setDrawingProperties(params) { 
    sigInst.drawingProperties(params);
    sigInst.draw();
}


function clearGEXF(){
    // Only possible because sigInst is declared globally outside of functions
    sigInst.emptyGraph();    
}

function zoomControl(direction, width, height) {
    var ratio = sigInst.position().ratio;
    switch (direction) {
        case 'in': 
            ratio *= zoomDelay;
            break;
        case 'out': 
            ratio /= zoomDelay;
            break;
    }
    sigInst.goTo(
        //$('.gexf-container').width() / 2,
        //$('.gexf-container').height() / 2,
        width / 2,
        height / 2, 
        ratio
    ); 
    
    
}
        