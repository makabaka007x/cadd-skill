# HDOCK 命令参考

## 二进制

当前仓库根目录下有两个核心可执行文件：

- `hdock`
- `createpl`

`hdock` 帮助信息显示的关键参数：

- `-spacing [1.2]`
- `-angle [15]`
- `-rsite [rsite.txt]`
- `-lsite [lsite.txt]`
- `-restr [restr.txt]`
- `-itscore [true/false]`
- `-out [Hdock.out]`

`createpl` 帮助信息显示的关键参数：

- `-complex`
- `-models`
- `-chid`
- `-nmax [100]`
- `-rmsd [5.0]`
- `-rsite [rsite.txt]`
- `-lsite [lsite.txt]`
- `-restr [restr.txt]`

## 最小示例

```bash
./hdock 1CGI_r_b.pdb 1CGI_l_b.pdb -out hdock.out
./createpl hdock.out models.pdb -nmax 20 -complex -models
```

## 文件约定

- 受体和配体输入为 PDB。
- `rsite.txt` / `lsite.txt` 为位点残基文件。
- 当前仓库示例 `rsite.txt` 内容为 `A:843`。
- `restr.txt` 为受体-配体约束文件；若格式来源不清楚，先查看用户已有文件，不要臆造。

## 建议交付物

对每个 case，优先保留：

- `hdock.out`
- `models.pdb`
- 原始输入副本
- stdout/stderr 日志
- 运行参数摘要
