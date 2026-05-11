# 特殊情况

## 非标准残基

当用户需要为特殊残基准备专用 `prepi` 和 `frcmod` 时，走 nonstandard 分支。
从 `assets/templates/nonstandard/leap.in` 起步，并按实际化学体系改写加载的参数文件。

## Zn 配位

当需要有键的 Zn 配位时，走 Zn 分支。
从 `assets/templates/zn/leap.in` 起步，并核对：

- 自定义原子类型
- 成键伙伴
- 实际结构里的金属和残基编号

## DNA 与 RNA

核酸体系统一走特殊分支。在 `tleap` 之前，把残基名和原子名清理规则说清楚，并在写平衡阶段 `.in` 文件前先确认 `restraintmask` 的对象。

- 预平衡默认目标是固定核酸主体重原子，让水和离子先重排。
- 对“只有核酸 + WAT/Na+/Cl-”的体系，可优先用 `!(:WAT,Na+,Cl-) & !@H=`。
- 如果还含蛋白、配体、Mg2+/Ca2+ 或其他共因子，不要直接套这个补集 mask；改成按实际要固定的主体写。
- 不要把 `(:WAT|Na+|Cl-)` 一类 mask 当成“约束 DNA”。

## 糖基化样共价连接

对于糖基化样或其他共价特殊连接，在 `tleap` 中显式写出 `bond` 指令，并把相关来源文件保留到 `prep/`。
