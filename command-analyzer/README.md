# redis-debug-tools



```

python analyzer.py --num 900000                                                                                                                            ok 
starting to capture, from 127.0.0.1 900000 commands!
General
========================================
Lines Processed: 900000  
Commands/Sec   : 36172.56


Latency Distribution
========================================
Median: 2.25 
75%   : 10.0 
90%   : 31.0 
99%   : 354.0


Biggest Contributors to Latency
========================================
MSET  : 11988726.0
LRANGE: 3941006.25
INCR  : 1725528.0 
SET   : 1634401.75
PING  : 1596635.0 
LPUSH : 1576625.0 
RPUSH : 1538774.25
GET   : 807861.25 


Command Breakdown
========================================
PING  : 200000
MSET  : 100000
SET   : 100000
GET   : 100000
INCR  : 100000
LPUSH : 100000
RPUSH : 100000
LRANGE: 95128 


Key Breakdown
========================================
mylist              : 300000
key:__rand_int__    : 300000
counter:__rand_int__: 100000


Prefix Breakdown
========================================
key    : 300000
counter: 100000


Slowest commands
========================================
8679632.0: "MSET" "key:__rand_int__" VXK key:__rand_int__ VXK key:__rand_int__ VXK ...
8200.0   : "MSET" "key:__rand_int__" VXK key:__rand_int__ VXK key:__rand_int__ VXK ...
4514.0   : "RPUSH" "mylist" VXK                                                       
4452.0   : "MSET" "key:__rand_int__" VXK key:__rand_int__ VXK key:__rand_int__ VXK ...
4110.25  : "MSET" "key:__rand_int__" VXK key:__rand_int__ VXK key:__rand_int__ VXK ...
4076.0   : "RPUSH" "mylist" VXK                                                       
3810.75  : "INCR" "counter:__rand_int__"                                              
3682.25  : "MSET" "key:__rand_int__" VXK key:__rand_int__ VXK key:__rand_int__ VXK ...

```
