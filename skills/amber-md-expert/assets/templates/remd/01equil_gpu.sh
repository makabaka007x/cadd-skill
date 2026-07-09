#!/bin/bash

#SBATCH -J amber-remd-equil
#SBATCH --partition=gpu
#SBATCH --qos=gpu
#SBATCH -N 1                    # Single node
#SBATCH --ntasks-per-node=1     
#SBATCH --cpus-per-task=4       
#SBATCH --gres=gpu:1
#SBATCH -o %j.out
#SBATCH -e %j.err

module load amber

# 设置错误时退出
set -e

echo "=========================================="
echo "开始GPU平衡: $(date)"
echo "=========================================="

# 31个温度
TEMPS=(310.00 311.61 313.22 314.84 316.47 318.10 319.75 321.40 
       323.05 324.71 326.38 328.05 329.73 331.42 333.11 334.82 
       336.53 338.24 339.97 341.69 343.43 345.18 346.93 348.69 
       350.45 352.22 354.00 355.79 357.59 359.39 360.00)

# ========== 最小化 ==========
echo "步骤1: 能量最小化..."
pmemd.cuda -O -i min.in -p system.prmtop -c system.inpcrd \
      -ref system.inpcrd \
      -o min.out -r min.rst

# 检查最小化结果
if [ ! -f min.rst ]; then
    echo "❌ 错误: 最小化失败！"
    echo "检查 min.out 文件"
    exit 1
fi
echo "✓ 最小化完成"

# ========== 升温和平衡 ==========
TOTAL=${#TEMPS[@]}
COUNT=0

for T in ${TEMPS[@]}; do
  COUNT=$((COUNT + 1))
  echo ""
  echo "=========================================="
  echo "进度: $COUNT / $TOTAL"
  echo "温度: $T K"
  echo "=========================================="
  
  # 升温
  echo "  升温中..."
  sed "s/TEMP/$T/" heat.in > heat_${T}.in
  
  pmemd.cuda -O -i heat_${T}.in -p system.prmtop \
             -c min.rst \
             -ref min.rst \
             -o heat_${T}.out \
             -r heat_${T}.rst \
             -x heat_${T}.nc
  
  # 检查升温结果
  if [ ! -f heat_${T}.rst ]; then
      echo "  ❌ 错误: 温度 $T K 升温失败！"
      echo "  检查 heat_${T}.out"
      exit 1
  fi
  echo "  ✓ 升温完成"
  
  # 平衡
  echo "  平衡中..."
  sed "s/TEMP/$T/" equil.in > equil_${T}.in
  
  pmemd.cuda -O -i equil_${T}.in -p system.prmtop \
             -c heat_${T}.rst \
             -o equil_${T}.out \
             -r equil_${T}.rst \
             -x equil_${T}.nc
  
  # 检查平衡结果
  if [ ! -f equil_${T}.rst ]; then
      echo "  ❌ 错误: 温度 $T K 平衡失败！"
      echo "  检查 equil_${T}.out"
      exit 1
  fi
  echo "  ✓ 平衡完成"
  
  # 清理中间文件（可选）
  # rm heat_${T}.nc heat_${T}.in
done

echo ""
echo "=========================================="
echo "所有温度平衡完成！"
echo "结束时间: $(date)"
echo "=========================================="

# 列出生成的文件
echo ""
echo "生成的平衡结构文件:"
ls -lh equil_*.rst | awk '{print $9, $5}'

echo ""
echo "准备运行REMD..."
