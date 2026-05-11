#!/bin/bash
# HADDOCK 2.5 辅助脚本
# 用于快速执行常见操作

HADDOCK_DIR="/path/to/haddock2.5"
EXAMPLES_DIR="$HADDOCK_DIR/examples"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 激活 HADDOCK 环境
activate_haddock() {
    echo -e "${GREEN}激活 HADDOCK 环境...${NC}"
    conda activate haddock2.5
    cd "$HADDOCK_DIR"
    source haddock_configure.sh
    echo -e "${GREEN}环境已激活${NC}"
}

# 检查环境状态
check_env() {
    echo "=== HADDOCK 环境检查 ==="

    # 检查 conda 环境
    if conda info --envs | grep -q "haddock2.5"; then
        echo -e "[${GREEN}✓${NC}] Conda 环境：haddock2.5 存在"
    else
        echo -e "[${RED}✗${NC}] Conda 环境：haddock2.5 不存在"
    fi

    # 检查 HADDOCK 目录
    if [ -d "$HADDOCK_DIR" ]; then
        echo -e "[${GREEN}✓${NC}] HADDOCK 目录：$HADDOCK_DIR"
    else
        echo -e "[${RED}✗${NC}] HADDOCK 目录不存在：$HADDOCK_DIR"
    fi

    # 检查 CNS
    if [ -x "$HADDOCK_DIR/cns1.3/cns"* ]; then
        echo -e "[${GREEN}✓${NC}] CNS 可执行文件：存在"
    else
        echo -e "[${YELLOW}!${NC}] CNS 可执行文件：未找到或无权限"
    fi

    # 检查配置文件
    if [ -f "$HADDOCK_DIR/haddock_configure.sh" ]; then
        echo -e "[${GREEN}✓${NC}] 配置文件：haddock_configure.sh"
    else
        echo -e "[${RED}✗${NC}] 配置文件不存在"
    fi
}

# 列出所有示例
list_examples() {
    echo "=== HADDOCK 示例列表 ==="
    echo ""
    printf "%-25s %-15s %-10s\n" "示例名称" "对接类型" "系统"
    echo "---------------------------------------------------------"
    printf "%-25s %-15s %-10s\n" "protein-protein" "蛋白 - 蛋白" "E2A-HPR"
    printf "%-25s %-15s %-10s\n" "protein-dna" "蛋白-DNA" "3CRO"
    printf "%-25s %-15s %-10s\n" "protein-ligand" "蛋白 - 小分子" "神经氨酸酶"
    printf "%-25s %-15s %-10s\n" "protein-peptide" "蛋白 - 多肽" "1NX1"
    printf "%-25s %-15s %-10s\n" "protein-peptide-ensemble" "集合 PRE" "SUMO-DAXX"
    printf "%-25s %-15s %-10s\n" "protein-protein-em" "冷冻电镜" "核糖体"
    printf "%-25s %-15s %-10s\n" "protein-protein-rdc" "RDC 约束" "双泛素"
    printf "%-25s %-15s %-10s\n" "protein-protein-pcs" "PCS 约束" "EPS-Hot"
    printf "%-25s %-15s %-10s\n" "protein-protein-dani" "DANI 约束" "E2A-HPR"
    printf "%-25s %-15s %-10s\n" "protein-trimer" "同源三聚体" "1QU9"
    printf "%-25s %-15s %-10s\n" "protein-tetramer-CG" "粗粒化四聚体" "3GD8"
    printf "%-25s %-15s %-10s\n" "solvated-docking" "溶剂化对接" "Barnase-Barstar"
    printf "%-25s %-15s %-10s\n" "protein-refine-pcs" "PCS 优化" "-"
    printf "%-25s %-15s %-10s\n" "refine-complex" "复合物优化" "-"
    printf "%-25s %-15s %-10s\n" "protein-ligand-shape" "形状约束" "BACE_1"
}

# 运行示例
run_example() {
    local example=$1
    local example_dir="$EXAMPLES_DIR/$example"

    if [ ! -d "$example_dir" ]; then
        echo -e "${RED}错误：示例 '$example' 不存在${NC}"
        echo "使用 'haddock examples' 查看可用示例"
        return 1
    fi

    echo -e "${GREEN}运行示例：$example${NC}"
    echo "目录：$example_dir"
    echo "日志：$example_dir/haddock.out"
    echo ""

    cd "$example_dir"

    # 检查是否已有运行目录
    if [ -d "run1" ]; then
        echo -e "${YELLOW}警告：run1 目录已存在${NC}"
        read -p "是否删除并重新开始？[y/N] " confirm
        if [ "$confirm" = "y" ]; then
            rm -rf run1
        else
            echo "取消运行"
            return 1
        fi
    fi

    # 启动运行
    echo "启动 HADDOCK..."
    nohup bash -c "
        source ../../haddock_configure.sh
        haddock2.5 >&/dev/null
        cd run1
        patch -p0 -i ../run.cns.patch >&/dev/null
        haddock2.5 >&haddock.out
    " > haddock.out &

    echo "运行已启动 (PID: $!)"
    echo "使用 'tail -f haddock.out' 查看日志"
}

# 查看运行状态
check_status() {
    local run_dir="${1:-run1}"

    if [ ! -d "$run_dir" ]; then
        echo -e "${RED}错误：运行目录 '$run_dir' 不存在${NC}"
        return 1
    fi

    echo "=== HADDOCK 运行状态 ==="
    echo "目录：$run_dir"
    echo ""

    # 检查各阶段
    for stage in it0 it1 water; do
        if [ -d "$run_dir/structures/$stage" ]; then
            local count=$(ls -d $run_dir/structures/$stage/*/ 2>/dev/null | wc -l)
            echo -e "[${GREEN}✓${NC}] $stage: $count 模型"
        else
            echo -e "[${YELLOW}-${NC}] $stage: 未开始"
        fi
    done

    echo ""

    # 显示日志尾部
    if [ -f "$run_dir/haddock.out" ]; then
        echo "=== 最新日志 ==="
        tail -20 "$run_dir/haddock.out"
    fi
}

# 清理运行目录
clean_run() {
    local run_dir="${1:-run1}"

    if [ ! -d "$run_dir" ]; then
        echo -e "${RED}错误：运行目录 '$run_dir' 不存在${NC}"
        return 1
    fi

    echo "将删除:"
    echo "  - $run_dir/structures/"
    echo "  - $run_dir/analysis/"
    echo "  - $run_dir/haddock.out"
    echo ""
    echo "保留:"
    echo "  - $run_dir/run.cns"
    echo "  - $run_dir/run.param"
    echo ""

    read -p "是否继续？[y/N] " confirm
    if [ "$confirm" = "y" ]; then
        rm -rf "$run_dir/structures" "$run_dir/analysis" "$run_dir/haddock.out"
        echo -e "${GREEN}清理完成${NC}"
    else
        echo "取消清理"
    fi
}

# 显示帮助
show_help() {
    echo "HADDOCK 2.5 辅助脚本"
    echo ""
    echo "用法：haddock.sh <command> [options]"
    echo ""
    echo "命令:"
    echo "  env              检查环境"
    echo "  activate         激活环境"
    echo "  examples         列出所有示例"
    echo "  run <name>       运行示例"
    echo "  status [dir]     查看状态"
    echo "  clean [dir]      清理结果"
    echo "  help             显示帮助"
    echo ""
    echo "示例:"
    echo "  haddock.sh run protein-protein"
    echo "  haddock.sh status run1"
    echo "  haddock.sh clean run1"
}

# 主程序
case "${1:-help}" in
    env|check)
        check_env
        ;;
    activate)
        activate_haddock
        ;;
    examples|list)
        list_examples
        ;;
    run)
        activate_haddock
        run_example "$2"
        ;;
    status)
        check_status "$2"
        ;;
    clean)
        clean_run "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}未知命令：$1${NC}"
        show_help
        exit 1
        ;;
esac
