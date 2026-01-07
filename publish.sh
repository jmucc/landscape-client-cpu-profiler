#!/bin/bash
lxc stop tf-landscape-server-noble tf-landscape-client-noble 
lxc publish tf-landscape-server-noble --alias tf-landscape-server-noble
lxc publish tf-landscape-client-noble --alias tf-landscape-client-noble
lxc start tf-landscape-server-noble tf-landscape-client-noble 