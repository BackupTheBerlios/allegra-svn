Allegra - Copyright (C) 2005 Laurent A.V. Szyster | Copyleft GPL 2.0

Allegra is an innovative library for Semantic Web applications development. 
It provides a Python framework for asynchronous network peer programming, 
a simple stack of Internet standards implementations, and two new network 
applications: a disruptive metabase and a practical web peer.

http://laurentszyster.be/blog/allegra/


INSTALL

extract this archive and change directory to the extracted root

	cd allegra

then install Allegra's library

	python setup.py install
	
	
RUN

start a PNS metabase peer first:

	python ./lib/pns_peer.py

then Allegra's semantic web peer:

	python ./lib/presto_http.py ./app
	
accessible from your browser at:

	http://127.0.0.1/
	
or if the port 80 is allready assigned, to one of your choice:

	python ./lib/presto_http.py ./app 127.0.0.1:8888
	
