#!/bin/bash
lxc stop tf-landscape-server-noble tf-landscape-client-noble 
lxc delete tf-landscape-server-noble tf-landscape-client-noble
lxc launch tf-landscape-server-noble tf-landscape-server-noble
lxc launch tf-landscape-client-noble tf-landscape-client-noble