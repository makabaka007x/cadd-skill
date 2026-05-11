#!/bin/bash

#SBATCH -J af3-2         # Job name
#SBATCH --partition=gpu4090     # gpu4090
#SBATCH --qos=4gpus
#SBATCH -N 1                    # Single node
#SBATCH --ntasks-per-node=1     
#SBATCH --cpus-per-task=4       
#SBATCH --gres=gpu:1            # 1 GPUs
#SBATCH -o %j.out         # Output result
#SBATCH -e %j.err          # Error output


ml load amber

#istart=1
#iend=3

#I=$istart
#while [ $I -le $iend ]
#do
#  suffix=`printf %03d $I`
#  suffix2=`printf %03d $((I-1))`
#  pmemd.cuda -O -i prod.in -o prod$suffix.out -p wbox.prmtop -c prod$suffix2.rst -x prod$suffix.nc -r prod$suffix.rst
#  I=$((I+1))
#done
pmemd.cuda -O -i 01min.in -p complex-amber.top -c complex-amber.crd -o min.out -x min.crd -inf min.info -r min.rst
pmemd.cuda -O -i 02heat.in -p complex-amber.top -c min.rst -ref min.rst -o heat.out -x heat.crd -inf heat.info -r heat.rst
pmemd.cuda -O -i 03equil01.in -p complex-amber.top -c heat.rst -ref heat.rst -o eq1.out -x eq1.crd -inf eq1.info -r eq1.rst
pmemd.cuda -O -i 03equil02.in -p complex-amber.top -c eq1.rst -ref eq1.rst -o eq2.out -x eq2.crd -inf eq2.info -r eq2.rst
pmemd.cuda -O -i md.in  -p complex-amber.top -c eq2.rst  -o md.out -x md.trj -r md.rst -ref eq2.rst