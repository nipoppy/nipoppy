datalad clone https://github.com/OpenNeuroDatasets/ds004101.git 
datalad get -r ds004101
# TODO dont really like this, our study is a symlink instead of a subdataset link
nipoppy init --dataset nipoppy_study --bids-source ds004101
cd nipoppy_study
datalad create --force .
datalad save -m "nipoppy init"
datalad run -m "Install pipeline" nipoppy pipeline install 15427844
# then manually update templateflow home
datalad save -m "set templateflow home"
datalad run -m "process single participant/session" nipoppy process \
--pipeline mriqc \
--pipeline-version 23.1.0 \
--participant-id 09114 \
--session-id 1pre
