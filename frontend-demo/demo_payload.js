/**
 * demo_payload.js — Stable demo data for competition recording.
 * Offline fallback only. All data centers on: 高等数学上册 · 函数极限.
 */
window.DEMO_PAYLOAD = {
  course: {
    name: "高等数学上册",
    topic: "函数极限",
    status: "本地演示知识库已连接"
  },

  question: "我不懂函数极限，讲清定义、常见误区，并给一个例题。我基础比较差。",

  answer: "函数极限研究的是：当自变量 x 越来越靠近某个点 x0 时，函数值 f(x) 是否越来越靠近一个确定的数 A。注意，极限关心的是“靠近过程中的趋势”，不是只看 x=x0 这一点的函数值。\n\n" +
    "一、先用直观话理解\n" +
    "把 x 想成一个学生一步步走向教室门口 x0，f(x) 是他每一步对应的位置高度。如果无论从左边走来还是从右边走来，f(x) 都越来越接近同一个数 A，我们就说函数在 x 趋向 x0 时的极限是 A。\n\n" +
    "二、严格定义要看什么\n" +
    "lim f(x)=A 的意思是：只要你要求函数值离 A 足够近，我总能要求 x 离 x0 足够近，并且在这个范围内 f(x) 都满足要求。这里不要求 f(x0) 一定有定义，也不要求 f(x0)=A。\n\n" +
    "三、常见误区\n" +
    "误区1：以为极限存在必须函数在该点有定义。实际不需要，极限看的是趋近趋势。\n" +
    "误区2：只从左边或右边看。函数极限存在必须左极限和右极限都存在且相等。\n" +
    "误区3：直接代入不检查条件。代入只是某些连续函数的快捷方法，不是所有题都能这么做。\n\n" +
    "四、例题\n" +
    "求 lim(x→1) (x^2-1)/(x-1)。当 x 不等于 1 时，(x^2-1)/(x-1)=(x-1)(x+1)/(x-1)=x+1，所以 x 趋近 1 时函数值趋近 2。虽然原式在 x=1 处分母为0没有定义，但极限仍然存在，等于2。\n\n" +
    "五、学习建议\n" +
    "先会判断“看趋势还是看点值”，再练左右极限是否相等，最后再做代数化简和等价无穷小等计算技巧。",

  citations: [
    {
      id: 1,
      title: "函数极限定义",
      source: "高数上.pdf",
      section: "第一章 函数与极限",
      snippet: "函数极限描述自变量趋近某点或无穷远时，函数值趋近某个确定数值的趋势。",
      relevance: "高"
    },
    {
      id: 2,
      title: "左右极限",
      source: "高数上.pdf",
      section: "第一章 函数与极限",
      snippet: "函数在一点的极限存在，需要左极限和右极限同时存在并且相等。",
      relevance: "高"
    },
    {
      id: 3,
      title: "无穷小与极限",
      source: "高数上.pdf",
      section: "第一章 函数与极限",
      snippet: "无穷小是以零为极限的变量，可用于理解和计算极限。",
      relevance: "中"
    }
  ],

  mindmap: {
    type: "tree",
    title: "函数极限学习框架",
    nodes: [
      { level: "root", text: "函数极限" },
      { level: "branch", text: "核心问题", children: [
        "x 趋近 x0 时 f(x) 是否趋近 A",
        "看趋近过程，不只看点值",
        "可用于定义连续、导数和积分"
      ]},
      { level: "branch", text: "判断条件", children: [
        "左极限存在",
        "右极限存在",
        "左右极限相等"
      ]},
      { level: "branch", text: "典型方法", children: [
        "直接代入：适用于连续函数",
        "因式分解：处理 0/0 型",
        "等价无穷小：简化局部变化",
        "夹逼准则：处理震荡或不易化简"
      ]},
      { level: "branch", text: "常见误区", children: [
        "把函数值等同于极限",
        "忽略左右极限",
        "不说明适用条件",
        "只背公式不看趋近方向"
      ]}
    ]
  },

  quiz: [
    {
      id: 1,
      question: "函数在 x0 处的极限存在，是否要求 f(x0) 一定有定义？",
      options: ["一定要求", "不要求", "只有多项式要求", "只有分式函数要求"],
      correctAnswer: 1,
      explanation: "极限关注 x 趋近 x0 时 f(x) 的趋势，不关注 x=x0 这一点是否有函数值。",
      knowledgePoint: "函数极限定义",
      difficulty: "基础"
    },
    {
      id: 2,
      question: "函数极限存在的关键条件是什么？",
      options: ["左极限和右极限存在且相等", "只看左极限", "只看右极限", "函数值必须等于0"],
      correctAnswer: 0,
      explanation: "两侧趋近同一个数时，双侧极限才存在。",
      knowledgePoint: "左右极限",
      difficulty: "基础"
    },
    {
      id: 3,
      question: "求 lim(x→1)(x²-1)/(x-1) 的正确思路是？",
      options: ["直接说不存在", "先因式分解再约去 x-1", "把 x=0 代入", "只看分母为0"],
      correctAnswer: 1,
      explanation: "x 不等于1时可化简为 x+1，因此趋近1时极限为2。",
      knowledgePoint: "0/0 型极限",
      difficulty: "基础"
    }
  ],

  studyPlan: [
    {
      step: 1,
      title: "先分清点值与趋势",
      goal: "理解极限不等于函数值，先建立直观图像",
      resource: "讲义 · 函数极限定义",
      estimatedTime: "12分钟",
      action: "读讲义前两节，画出 x 趋近 x0 的箭头"
    },
    {
      step: 2,
      title: "补左右极限",
      goal: "会判断双侧极限是否存在",
      resource: "知识树 · 左右极限",
      estimatedTime: "15分钟",
      action: "对照导图，把左右极限相等作为判断清单"
    },
    {
      step: 3,
      title: "做一个 0/0 型例题",
      goal: "掌握因式分解消去无意义点的基本套路",
      resource: "练习题 · 函数极限",
      estimatedTime: "18分钟",
      action: "完成 3 道选择题，选错后看错因"
    },
    {
      step: 4,
      title: "用错题更新路径",
      goal: "根据错因决定是补定义、补代数化简还是补左右极限",
      resource: "学习报告 · 薄弱点",
      estimatedTime: "10分钟",
      action: "查看学习报告，按推荐资源复习"
    }
  ],

  learningReport: {
    total_attempts: 3,
    correct_count: 2,
    accuracy: 0.67,
    weak_points: ["函数极限定义", "左右极限", "0/0 型极限"],
    recommended_resources: [
      { type: "lecture_doc", title: "函数极限定义讲义" },
      { type: "mindmap", title: "函数极限知识结构图" },
      { type: "quiz", title: "左右极限专项练习" }
    ],
    profile_updated: true
  },

  agentSteps: [
    { title: "Tutor Agent", description: "识别问题：函数极限定义、常见误区、基础薄弱", status: "completed" },
    { title: "Retriever Agent", description: "检索《高数上.pdf》第一章函数与极限片段", status: "completed" },
    { title: "Verifier Agent", description: "基础可信度校验：引用覆盖与风险等级", status: "completed" },
    { title: "Practice Agent", description: "生成讲义、知识树、练习题、学习路径和 Markdown PPT", status: "completed" },
    { title: "Profile Agent", description: "更新薄弱点：定义理解、左右极限、例题步骤", status: "completed" }
  ],

  mermaidDiagram: "mindmap\n  root((函数极限))\n    核心定义\n      x趋近x0\n      f(x)趋近A\n      看趋势不只看点值\n    左右极限\n      左极限存在\n      右极限存在\n      两者相等\n    常见方法\n      直接代入\n      因式分解\n      等价无穷小\n    常见误区\n      把函数值当极限\n      忽略左右极限\n      不说明适用条件"
};
