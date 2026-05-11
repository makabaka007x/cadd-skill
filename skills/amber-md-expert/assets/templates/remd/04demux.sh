#!/bin/bash
# demux.sh

#SBATCH -J REMD-CPU        # Job name
#SBATCH --partition=cpu8358     # gpua800
#SBATCH --qos=52cores
#SBATCH -N 1                    # Single node
#SBATCH --ntasks-per-node=32
#SBATCH --cpus-per-task=10
#SBATCH -o %j.out         # Output result
#SBATCH -e %j.err          # Error output

module load amber

cat > demux.cpptraj << EOF
# 读取所有31个副本
$(for i in {0..30}; do echo "trajin replica_$i.nc"; done)

# 提取310K轨迹
temperature rem.log 310.0 demux T310

# 也可提取其他温度
temperature rem.log 320.0 demux T320
temperature rem.log 330.0 demux T330
temperature rem.log 340.0 demux T340
temperature rem.log 350.0 demux T350
temperature rem.log 360.0 demux T360

run
quit
EOF

cpptraj -p system.prmtop -i demux.cpptraj

echo "Demux完成"
