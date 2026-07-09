#!/bin/bash

#SBATCH -J amber-membrane
#SBATCH --partition=gpu
#SBATCH --qos=gpu
#SBATCH -N 1                    # Single node
#SBATCH --ntasks-per-node=1     
#SBATCH --cpus-per-task=4       
#SBATCH --gres=gpu:1
#SBATCH -o %j.out
#SBATCH -e %j.err


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
pmemd.cuda -O -i 0_minimization.mdin -p input.parm7 -c input.rst7 -o 0_minimization.out -r 0_minimization.rst -ref input.rst7
pmemd.cuda -O -i 1_equilibration.mdin -p input.parm7 -c 0_minimization.rst -o 1_equilibration.out -r 1_equilibration.rst -ref 0_minimization.rst
pmemd.cuda -O -i 2_equilibration.mdin -p input.parm7 -c 1_equilibration.rst -o 2_equilibration.out -r 2_equilibration.rst -ref 1_equilibration.rst
pmemd.cuda -O -i 3_equilibration.mdin -p input.parm7 -c 2_equilibration.rst -o 3_equilibration.out -r 3_equilibration.rst -ref 2_equilibration.rst
pmemd.cuda -O -i 4_equilibration.mdin -p input.parm7 -c 3_equilibration.rst -o 4_equilibration.out -r 4_equilibration.rst -ref 3_equilibration.rst
pmemd.cuda -O -i 5_equilibration.mdin -p input.parm7 -c 4_equilibration.rst -o 5_equilibration.out -r 5_equilibration.rst -ref 4_equilibration.rst
pmemd.cuda -O -i 6_equilibration.mdin -p input.parm7 -c 5_equilibration.rst -o 6_equilibration.out -r 6_equilibration.rst -ref 5_equilibration.rst
pmemd.cuda -O -i 7_production.mdin -p input.parm7 -c 6_equilibration.rst -o md.out -x md.trj -r md.rst -ref 6_equilibration.rst
