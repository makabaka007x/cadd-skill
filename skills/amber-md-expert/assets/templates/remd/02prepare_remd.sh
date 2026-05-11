#!/bin/bash
# prepare_remd.sh

TEMPS=(310.00 311.61 313.22 314.84 316.47 318.10 319.75 321.40 
       323.05 324.71 326.38 328.05 329.73 331.42 333.11 334.82 
       336.53 338.24 339.97 341.69 343.43 345.18 346.93 348.69 
       350.45 352.22 354.00 355.79 357.59 359.39 360.00)

N=${#TEMPS[@]}
echo "副本数: $N"

# 生成输入文件
for i in $(seq 0 $((N-1))); do
  T=${TEMPS[$i]}
  sed "s/TEMP/$T/" remd.in > remd_$i.in
  cp equil_${T}.rst replica_$i.rst
  echo "副本 $i: $T K"
done

# 生成groupfile
> groupfile
for i in $(seq 0 $((N-1))); do
  echo "-O -rem 1 -remlog rem.log -i remd_$i.in -p system.prmtop -c replica_$i.rst -o replica_$i.out -r replica_$i.rst -x replica_$i.nc" >> groupfile
done

echo "完成"
