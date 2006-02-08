# Note about this implementation
#
# This is a good demonstration of how to move from a synchrous design
# to an asynchronous one. First make a synchronous pipe that works
# asynchronously internally but can be used from the command line with
# other synchronized pipes. Give it a simple web interface using the
# stock PRESTo synchronized method:
#
#        <presto:pipe
#                command="python -OO pns_rss.py"
#                options="http://feed/"
#                />
#
# The strange thing about the stock PRESTo system pipe is that it returns
# immediately ... with a new state: a new "job". Remember the good all batch
# days? As the synchronous job proceeds its output is buffered by this
# element, its status (time, size, etc ...) updated until it exits.
#
# Many jobs will close or redirect stderr and stdout, only reporting
# their status as they exit. There is no reason to hang a connection
# waiting for no synchronous result. And that will be the simplest case,
# how most new pipes will come to be first, before they are integrated
# in an XML data flow.
#
# Other, more elaborated jobs will yield some XML status (usually on stderr)
# and long jobs may block a synchronized queue and all other synchronized
# instances using it. That's why its called a job: because CPU time is 
# rationned, along with all the resources consumed by synchronous services.
#
# That's a feature not a bug!
#
# Let's take a "real-world" implementation of PRESTo. 

# If "slow" synchronous batch processes must be integrated with PRESTo,
# there is little chance that other kind of synchronized processes will
# be served by the same host.
#
# Small, more granular synchronous process (like a BSDDB access) are
# expected to be found along asynchronous methods, developped for PRESTo
# not *before*. It makes no sense to develop a new asynchronous SOA on the
# same hosts were legacy applications are in production! So it is both safe
# and practical *not* to dedicate a thread for each job batched.
#
# With PRESTo, system administrators can easely set a high-enough limit
# on  the number of synchronized thread queue available to handle jobs.
# Exactly as they do with Apache, yet with the ability to develop an
# asynchronous web interface for their job management. 
#
# And the best part is that users won't even notice about rationning.
# Because the response to job submission and its status are managed and
# available asynchronously to the web browser. Checking the status of
# a synchronized job (like a CC submission) is as fast as it can be ...
# asynchronously.

