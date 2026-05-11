#!/bin/bash

#SBATCH -J EutC         # Job name
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
pmemd.cuda -O -i min1.in -p complex-amber.top -c complex-amber.crd -o min1.out -r min1.rst -ref complex-amber.crd
pmemd.cuda -O -i min2.in -p complex-amber.top -c min1.rst -o min2.out -r min2.rst -ref min1.rst
pmemd.cuda -O -i min3.in -p complex-amber.top -c min2.rst -o min3.out -r min3.rst -ref min2.rst
pmemd.cuda -O -i heat.in -p complex-amber.top -c min3.rst -o heat.out -r heat.rst -ref min3.rst
pmemd.cuda -O -i nvt.in  -p complex-amber.top -c heat.rst -o nvt.out -x nvt.trj -r nvt.rst -ref heat.rst
pmemd.cuda -O -i npt1.in  -p complex-amber.top -c nvt.rst -o npt1.out -x npt1.trj -r npt1.rst -ref nvt.rst
pmemd.cuda -O -i npt2.in  -p complex-amber.top -c npt1.rst  -o npt2.out -x npt2.trj -r npt2.rst -ref npt1.rst
pmemd.cuda -O -i npt3.in  -p complex-amber.top -c npt2.rst  -o npt3.out -x npt3.trj -r npt3.rst -ref npt2.rst
pmemd.cuda -O -i npt4.in  -p complex-amber.top -c npt3.rst  -o npt4.out -x npt4.trj -r npt4.rst -ref npt3.rst
pmemd.cuda -O -i md.in  -p complex-amber.top -c npt4.rst  -o md.out -x md.trj -r md.rst -ref npt4.rst
