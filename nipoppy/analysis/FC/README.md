# Directory for FC analysis code

## Current analyses
	- Create an average FC matrix figure
    - Create an average FC matrix figure segmented over 7 YEO networks  
    - Create a figure showing distribution of FC values between pairs of YEO networks across PD and CTRL subjects
    - Create figures showing distribution of several graph properties measured based on FC values across PD and CTRL subjects
	
#### FC Analysis
	- In order to generate the analysis figures for FC, run the python script after setting a few important parameters and paths at the top of the code.
	- set paths to FC measurements and demographics, as well as the output directory
    - set the parameters related to brain scan, e.g. session id, task, as well as the brain atlases used for parcellation.
    - set the parameters related to PD/CTRL labels in the demographics/manifest
    - set paramters related to calculating graph properties and a list of desired graph properties to be calculated.

