#!/bin/bash

#SBATCH -J REMD-CPU        # Job name
#SBATCH --partition=cpu8358     # gpua800
#SBATCH --qos=52cores
#SBATCH -N 1                    # Single node
#SBATCH --ntasks-per-node=31
#SBATCH --cpus-per-task=1
#SBATCH -o %j.out         # Output result
#SBATCH -e %j.err          # Error output

module load amber/22
module load intel-mpi

N_REPLICAS=8

echo "开始REMD: $(date)"
echo "副本数: $N_REPLICAS"

mpirun -np $N_REPLICAS \
       sander.MPI \
       -ng $N_REPLICAS \
       -groupfile groupfile

echo "完成: $(date)"

# 快速检查
echo "交换率:"
python3 << 'EOF'
import re
with open('rem.log') as f:
    lines = f.readlines()
total = sum(1 for l in lines if 'Exchange between' in l)
accept = sum(1 for l in lines if 'Accepted' in l)
if total > 0:
    print(f"{accept}/{total} = {100*accept/total:.1f}%")
EOF