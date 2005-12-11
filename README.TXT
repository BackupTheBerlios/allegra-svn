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

	python allegra_pns.py

you are now ready to run Allegra's semantic web peer:

	python allegra_presto.py
	
accessible from your browser at:

	http://127.0.0.1/
	
or if the port 80 is allready assigned to the one of your choice:

	python allegra_presto.py 8080
	
