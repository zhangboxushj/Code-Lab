# LoRA 微调知识库

## LoRA 简介
LoRA（Low-Rank Adaptation）是一种参数高效的大模型微调方法，由微软研究院提出。核心思想是在原始权重矩阵旁边添加低秩矩阵分解，只训练新增的低秩矩阵，冻结原始权重。

## 关键参数

### Rank（秩，r）
- 控制低秩矩阵的维度大小
- 常用值：4、8、16、32、64
- Rank 越大，可训练参数越多，表达能力越强，但显存占用也越大
- 一般任务推荐从 r=8 开始调试
- 对于复杂任务或领域差异大的场景，可以尝试 r=16 或 r=32

### Alpha（lora_alpha）
- LoRA 更新的缩放系数，实际缩放比例为 alpha/rank
- 通常设置为 rank 的 1~2 倍，如 rank=8 时 alpha=16
- Alpha 越大，LoRA 权重对原始模型影响越大
- 建议保持 alpha/rank 比值在 1~2 之间

### Dropout（lora_dropout）
- 对 LoRA 层的 dropout 正则化，防止过拟合
- 通常设置为 0.05~0.1
- 数据量少时适当增大（0.1~0.2）
- 数据量充足时可设为 0

## 代码示例

```python
from peft import LoraConfig, get_peft_model

config = LoraConfig(
    r=8,                    # rank
    lora_alpha=16,          # alpha
    lora_dropout=0.05,      # dropout
    target_modules=["q_proj", "v_proj"],  # 目标模块
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(base_model, config)
model.print_trainable_parameters()
```

## 对模型效果的影响

### Rank 的影响
- Rank 过小：模型表达能力不足，欠拟合
- Rank 过大：参数量增加，可能过拟合，训练变慢
- 最优 rank 取决于任务复杂度和数据量

### Alpha 的影响
- Alpha 过小：LoRA 更新对模型影响微弱，学习效果差
- Alpha 过大：可能破坏原始模型的预训练知识
- 建议通过验证集调优

### 目标模块选择
- 通常选择 attention 层的 q_proj、v_proj
- 也可以加入 k_proj、o_proj、gate_proj 等
- 模块越多，参数量越大，效果通常越好但训练越慢

---

# Transformer 架构

## Self-Attention 机制

### 计算过程
1. 输入 X 通过三个线性变换得到 Q、K、V
2. 计算注意力分数：Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V
3. 多头注意力：将 d_model 分成 h 个头，并行计算后拼接

### 计算复杂度
- 时间复杂度：O(n²·d)，n 为序列长度，d 为特征维度
- 空间复杂度：O(n²)，需要存储注意力矩阵
- 长序列时（n > 2048）计算量急剧增长

### 优化方案

#### FlashAttention
- 不改变计算结果，通过 IO 感知的分块计算减少 HBM 读写
- 速度提升 2~4x，显存减少 5~20x
- PyTorch 2.0+ 已内置

```python
import torch.nn.functional as F
output = F.scaled_dot_product_attention(q, k, v, is_causal=True)
```

#### Multi-Query Attention (MQA)
- 多个 Query head 共享同一组 K、V
- 大幅减少 KV Cache 显存，推理速度提升明显
- 用于 PaLM、Falcon 等模型

#### Grouped-Query Attention (GQA)
- MHA 和 MQA 的折中方案
- 将 Query head 分组，每组共享一对 K、V
- 用于 LLaMA2、Mistral 等模型

---

# 大模型训练技术

## 混合精度训练
- 使用 FP16/BF16 进行前向和反向传播
- 保留 FP32 的主权重用于参数更新
- 显存减少约 50%，训练速度提升 2~3x

## 梯度检查点（Gradient Checkpointing）
- 不保存中间激活值，反向传播时重新计算
- 显存减少约 60~70%，训练时间增加约 30%
- 适合显存不足的场景

## DeepSpeed ZeRO
- ZeRO-1：分片优化器状态
- ZeRO-2：分片优化器状态 + 梯度
- ZeRO-3：分片优化器状态 + 梯度 + 模型参数
- 支持训练超大规模模型

---

# 模型评估指标

## 语言模型
- Perplexity（困惑度）：越低越好
- BLEU：机器翻译质量评估
- ROUGE：文本摘要质量评估

## 分类任务
- Accuracy、Precision、Recall、F1
- AUC-ROC

## 生成任务
- Human Evaluation：人工评估
- GPT-4 Evaluation：用 GPT-4 打分
- BERTScore：基于语义相似度的评估
