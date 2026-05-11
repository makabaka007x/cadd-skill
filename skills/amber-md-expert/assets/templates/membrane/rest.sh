#!/bin/bash

#cnt=1
#cntmax=6
fc=(250.0 100.0 50.0 50.0 25.0 10.0 5.0)
#echo $cnt

for i in {0..5}
do
	j=$i+1
	sed -e "s/FC/${fc[$j]}/g" dihe.restraint > step6.$i.rest
	
done
