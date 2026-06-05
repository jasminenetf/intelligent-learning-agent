/**
 * demo_payload.js — Stable demo data for competition recording
 * Provides complete AI intro course learning flow even when backend is slow or offline.
 * All data centered on: 人工智能导论 · 过拟合与正则化
 */
window.DEMO_PAYLOAD = {
  course: {
    name: "人工智能导论",
    topic: "过拟合与正则化",
    status: "课程资料已连接"
  },

  question: "我在学习人工智能导论，机器学习基础一般，容易混淆过拟合和欠拟合。请帮我理解过拟合和正则化的关系。",

  answer: "过拟合和正则化是机器学习中的核心概念。一句话总结：过拟合是模型把训练数据的噪声也学进去了，导致泛化能力差；正则化是给模型加上约束，防止它学得太死记硬背。\n\n" +
    "一、什么是过拟合\n" +
    "过拟合是指模型在训练集上表现很好，但在测试集或新数据上表现很差。就像学生只背了练习题的答案，换一道题就不会了。常见原因包括：模型过于复杂、训练数据太少、训练时间过长。\n\n" +
    "二、什么是欠拟合\n" +
    "欠拟合恰恰相反，模型连训练集上都表现不好。就像学生连基本概念都没掌握。常见原因：模型太简单、特征不够、训练不充分。\n\n" +
    "三、正则化如何缓解过拟合\n" +
    "正则化通过在损失函数中添加惩罚项来限制模型复杂度：\n" +
    "L1 正则化（Lasso）：倾向于产生稀疏权重，自动进行特征选择\n" +
    "L2 正则化（Ridge）：让权重整体变小但不为0，防止单个特征主导预测\n" +
    "Dropout：训练时随机丢弃部分神经元，强迫网络学习更鲁棒的特征\n" +
    "早停法：在验证集误差开始上升时停止训练，避免过度拟合训练数据\n\n" +
    "四、训练集与验证集的作用\n" +
    "训练集用于学习模型参数\n" +
    "验证集用于调整超参数和检测过拟合\n" +
    "测试集用于最终评估泛化能力\n" +
    "如果训练误差远小于验证误差，就是过拟合的典型信号\n\n" +
    "五、学习建议\n" +
    "先理解偏差-方差权衡的概念\n" +
    "在实践中对比有无正则化的模型表现\n" +
    "注意观察训练曲线：训练误差和验证误差的差距\n" +
    "从简单模型开始，逐步增加复杂度",

  citations: [
    {
      id: 1,
      title: "过拟合与欠拟合",
      source: "人工智能导论课程资料",
      section: "模型评估与选择",
      snippet: "过拟合指模型在训练集上表现优秀，但在新样本上泛化能力显著下降。通常发生在模型复杂度过高而训练数据相对不足时。",
      relevance: "高"
    },
    {
      id: 2,
      title: "正则化方法",
      source: "人工智能导论课程资料",
      section: "模型优化",
      snippet: "正则化通过给损失函数添加惩罚项来限制模型复杂度。L1产生稀疏解用于特征选择，L2约束权重幅度防止过拟合。",
      relevance: "高"
    },
    {
      id: 3,
      title: "训练集与验证集划分",
      source: "人工智能导论课程资料",
      section: "实验设计",
      snippet: "合理划分训练集、验证集和测试集是评估泛化能力的基础。验证集用于调参和早停判断，测试集仅在最终评估时使用。",
      relevance: "高"
    },
    {
      id: 4,
      title: "偏差-方差权衡",
      source: "人工智能导论课程资料",
      section: "理论基础",
      snippet: "偏差描述模型预测与真实值的偏离程度，方差描述模型对训练数据波动的敏感度。过拟合对应高方差，欠拟合对应高偏差。",
      relevance: "中"
    }
  ],

  mindmap: {
    type: "tree",
    title: "过拟合与正则化知识框架",
    nodes: [
      { level: "root", text: "过拟合与正则化" },
      { level: "branch", text: "过拟合", children: [
        "训练误差低，测试误差高",
        "模型复杂度过高",
        "数据量不足",
        "高方差"
      ]},
      { level: "branch", text: "欠拟合", children: [
        "训练和测试误差都高",
        "模型过于简单",
        "高偏差"
      ]},
      { level: "branch", text: "正则化方法", children: [
        "L1 (Lasso) — 特征选择",
        "L2 (Ridge) — 权重衰减",
        "Dropout — 随机丢弃神经元",
        "早停法 — 验证误差上升时停止"
      ]},
      { level: "branch", text: "训练集/验证集", children: [
        "训练集：学习参数",
        "验证集：调参+检测过拟合",
        "测试集：最终评估"
      ]},
      { level: "branch", text: "解决策略", children: [
        "增加训练数据",
        "降低模型复杂度",
        "使用正则化",
        "交叉验证"
      ]}
    ]
  },

  quiz: [
    {
      id: 1,
      question: "过拟合的主要表现是什么？",
      options: ["训练误差低，测试误差高", "训练和测试误差都低", "训练误差高，测试误差低", "训练和测试误差都高"],
      correctAnswer: 0,
      explanation: "过拟合的典型特征就是训练集上表现很好但测试集上表现差，说明模型泛化能力不足。",
      knowledgePoint: "过拟合",
      difficulty: "基础"
    },
    {
      id: 2,
      question: "L2正则化又称为什么？",
      options: ["Lasso", "Ridge回归", "Dropout", "早停法"],
      correctAnswer: 1,
      explanation: "L2正则化通过在损失函数中添加权重平方和惩罚项，又称Ridge回归或权重衰减。",
      knowledgePoint: "正则化",
      difficulty: "基础"
    },
    {
      id: 3,
      question: "Dropout在训练时随机丢弃什么？",
      options: ["权重", "偏置", "神经元", "梯度"],
      correctAnswer: 2,
      explanation: "Dropout在每次训练迭代中随机丢弃一部分神经元，强迫网络不依赖特定神经元，从而增强泛化能力。",
      knowledgePoint: "正则化",
      difficulty: "基础"
    },
    {
      id: 4,
      question: "以下哪个不是防止过拟合的方法？",
      options: ["增加训练数据", "使用L2正则化", "增加模型层数", "早停法"],
      correctAnswer: 2,
      explanation: "增加模型层数会增加模型复杂度，反而可能导致更严重的过拟合。其他三项都是防止过拟合的有效方法。",
      knowledgePoint: "过拟合",
      difficulty: "进阶"
    },
    {
      id: 5,
      question: "验证集的主要作用是什么？",
      options: ["训练模型参数", "调整超参数和检测过拟合", "最终评估模型", "数据预处理"],
      correctAnswer: 1,
      explanation: "验证集用于超参数调优和过拟合检测。训练集用于学习参数，测试集用于最终评估。",
      knowledgePoint: "训练集与验证集",
      difficulty: "基础"
    }
  ],

  studyPlan: [
    {
      step: 1,
      title: "理解过拟合",
      goal: "通过对比训练集和测试集误差，建立过拟合和欠拟合的直观理解",
      resource: "课程资料 · 模型评估章节",
      estimatedTime: "20分钟",
      action: "阅读过拟合定义，观察训练误差与测试误差的差距"
    },
    {
      step: 2,
      title: "区分欠拟合",
      goal: "了解模型过于简单导致训练和测试误差都高的情况",
      resource: "AI 讲解 · 偏差-方差权衡",
      estimatedTime: "15分钟",
      action: "对比过拟合和欠拟合的特征，理解偏差-方差权衡"
    },
    {
      step: 3,
      title: "学习正则化",
      goal: "掌握L1/L2正则化和Dropout的原理与使用场景",
      resource: "课程资料 · 正则化方法",
      estimatedTime: "30分钟",
      action: "理解正则化如何在损失函数中添加惩罚项来限制复杂度"
    },
    {
      step: 4,
      title: "完成巩固练习",
      goal: "通过测验检验对过拟合和正则化的理解程度",
      resource: "自适应测验",
      estimatedTime: "20分钟",
      action: "完成5道练习题，关注薄弱知识点"
    },
    {
      step: 5,
      title: "复盘薄弱点",
      goal: "回顾错题和薄弱知识点，强化理解",
      resource: "学习报告 · 错题回顾",
      estimatedTime: "15分钟",
      action: "回顾错题对应的知识点，必要时查阅课程资料加深理解"
    }
  ],

  learningReport: {
    total_attempts: 5,
    correct_count: 4,
    accuracy: 0.8,
    weak_points: ["正则化", "过拟合检测"],
    recommended_resources: [
      { type: "mindmap", title: "过拟合与正则化知识结构图" },
      { type: "quiz", title: "正则化专项练习" },
      { type: "lecture_doc", title: "模型评估与选择讲义" }
    ],
    profile_updated: true
  },

  agentSteps: [
    { title: "画像分析", description: "识别你的学习基础、目标和偏好", status: "completed" },
    { title: "课程资料检索", description: "从人工智能导论课程资料中查找相关内容", status: "completed" },
    { title: "可信答案校验", description: "检查回答是否有课程资料依据", status: "completed" },
    { title: "学习资源生成", description: "生成知识结构、测验和学习路径", status: "completed" },
    { title: "学习路径规划", description: "根据你的薄弱点规划学习顺序", status: "completed" }
  ]
};
