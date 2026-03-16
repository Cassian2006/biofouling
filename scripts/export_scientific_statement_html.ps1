param(
    [string]$OutputDir = "$HOME\Desktop\biofouling_science_upgrade"
)

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$outputPath = Join-Path $OutputDir 'scientific_statement.html'

$html = @"
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>科学性说明</title>
  <style>
    body {
      margin: 0;
      font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
      background: #f4f7fb;
      color: #162033;
    }
    .page {
      width: min(1040px, calc(100% - 40px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }
    .hero, .panel, .card {
      background: #fff;
      border: 1px solid #d8e0ee;
      border-radius: 18px;
      box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
    }
    .hero {
      padding: 26px 28px;
      margin-bottom: 18px;
    }
    .kicker {
      margin: 0 0 8px;
      font-size: 12px;
      letter-spacing: 0.12em;
      color: #2563eb;
      text-transform: uppercase;
      font-weight: 700;
    }
    h1 {
      margin: 0 0 12px;
      font-size: 34px;
      line-height: 1.15;
    }
    h2 {
      margin: 0 0 10px;
      font-size: 24px;
    }
    h3 {
      margin: 0 0 8px;
      font-size: 18px;
    }
    p, li {
      line-height: 1.82;
      color: #334155;
      font-size: 15px;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }
    .card {
      padding: 16px;
    }
    .panel {
      padding: 24px 28px;
      margin-top: 18px;
    }
    .two-col {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }
    .formula {
      margin: 12px 0 16px;
      padding: 12px 14px;
      border-radius: 12px;
      background: #eef4ff;
      color: #1d4ed8;
      font-family: Consolas, "Courier New", monospace;
      font-size: 14px;
      line-height: 1.65;
      white-space: pre-wrap;
    }
    .tag {
      display: inline-block;
      margin: 0 8px 8px 0;
      padding: 6px 10px;
      border-radius: 999px;
      background: #e2ecff;
      color: #1d4ed8;
      font-size: 13px;
      font-weight: 600;
    }
    ul {
      margin: 8px 0 14px;
      padding-left: 22px;
    }
    @media (max-width: 900px) {
      .cards, .two-col {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <p class="kicker">Scientific Statement</p>
      <h1>科学性说明正式材料</h1>
      <p>这份页面用于直接说明平台当前能回答什么、不能回答什么，以及各评分与深度模块在竞赛语境下应如何被准确解释。它不是源码说明，而是面向答辩、评审和项目汇报的正式口径材料。</p>
    </section>

    <section class="cards">
      <article class="card">
        <h3>FPI / ECP / RRI</h3>
        <p>明确三类核心评分分别回答什么问题，避免把 FPI 当成真实污损厚度，把 ECP 当成正式碳核算，把 RRI 当成真实污损地图。</p>
      </article>
      <article class="card">
        <h3>LSTM 与异常检测</h3>
        <p>区分短期趋势预测与异常筛查两条深度模块，说明哪些对象可预测，哪些对象只能进入异常解释链路。</p>
      </article>
      <article class="card">
        <h3>机制支撑与启发式边界</h3>
        <p>把已有机制支撑、当前仍属工程启发式近似，以及已经完成和仍待补强的部分统一写清，便于评审时快速说明。</p>
      </article>
    </section>

    <section class="panel">
      <h2>一、FPI 为什么是“行为主导、环境修正、维护轻修正”</h2>
      <p>FPI 当前回答的是：在当前时间窗内，这艘船在其实际行为模式、所处环境和维护背景下，是否更容易形成污损积累倾向。它不是在直接判断真实污损厚度，也不是在测量船底已经长了多少。</p>
      <p>行为之所以是主因，是因为污损积累首先取决于暴露是否真的发生：船是否长期低速、停留、锚泊、靠港。环境可以改变暴露后果，但如果船始终高速通过，环境再适宜，也不应直接被打成高污损倾向。</p>
      <div>
        <span class="tag">行为主导</span>
        <span class="tag">环境修正</span>
        <span class="tag">维护轻修正</span>
      </div>
      <div class="formula">EnvModifier = 0.40T + 0.20S + 0.25P + 0.15H
EnvAdj = 0.85 + 0.30 × EnvModifier
MaintenanceAdj = 0.90 + 0.20 × MaintenanceScore
FPI = BehaviorExposure × EnvAdj × MaintenanceAdj</div>
      <ul>
        <li>行为主导：先看这艘船到底慢了多久、停了多久、靠港多久。</li>
        <li>环境修正：环境既可以增强，也可以削弱风险，但不替代行为本身。</li>
        <li>维护轻修正：刚维护过的船和长期未维护的船，在同样暴露下不应完全等价，但维护也不应主导整个 FPI。</li>
      </ul>
    </section>

    <section class="panel">
      <h2>二、ECP 为什么只能做相对惩罚，不是正式碳核算</h2>
      <p>ECP 当前没有接入真实船型阻力曲线、主机工况、燃油模型和正式碳排放核算规则，因此它不具备被解释为正式碳核算结果的条件。</p>
      <p>它当前真正表达的是：当一艘船已经具有较高污损倾向时，长期未维护和持续高暴露会进一步放大潜在能耗与运营代价。</p>
      <div class="formula">CarbonPenaltyModifier = 1 + 0.18 × MaintenanceBurden + 0.12 × PersistentExposure
ECP = FPI × CarbonPenaltyModifier</div>
      <ul>
        <li>适合解释为：相对能耗惩罚指标、维护优先级辅助项。</li>
        <li>不适合解释为：正式碳核算、真实燃油消耗、正式排放申报结果。</li>
      </ul>
    </section>

    <section class="panel">
      <h2>三、RRI 为什么是区域综合风险图层，而不是“真实污损地图”</h2>
      <p>区域层没有真实船体污损观测网格，因此当前不可能直接画出“真实污损地图”。RRI 更接近于表达一片区域是否具有促进污损积累的综合条件。</p>
      <div class="formula">RRI = 0.40 × EnvModifier + 0.25 × Traffic + 0.20 × StayProb + 0.15 × PortAnchorageIntensity</div>
      <ul>
        <li>环境适宜性：这片水本身是否更适合附着生物维持活性。</li>
        <li>交通疏密：这里船流是否更密。</li>
        <li>停留概率：这里是否更容易出现低速和停泊。</li>
        <li>港口 / 锚地强度：这里是否是典型的港锚参考层热点。</li>
      </ul>
      <p>因此，RRI 适合解释为区域综合风险图层，不适合被解释为真实污损现状图或生态实测图。</p>
    </section>

    <section class="panel two-col">
      <div class="card">
        <h2>四、LSTM 回答什么问题</h2>
        <p>LSTM 回答的是：这艘船在最近一段连续历史暴露之后，下一时间窗的 FPI proxy 会往哪里走。</p>
        <ul>
          <li>它是短期趋势预测，不是长期生态预测。</li>
          <li>它预测的是下一时间窗风险，不是真实污损厚度。</li>
          <li>只有具备足够连续历史窗口的对象才能预测，不是所有船都能预测。</li>
        </ul>
      </div>
      <div class="card">
        <h2>五、异常检测回答什么问题</h2>
        <p>异常检测回答的是：这艘船的暴露模式是否明显偏离当前样本中的常规模式。</p>
        <ul>
          <li>它是异常筛查，不是“真实污损已发生”的证明。</li>
          <li>它适合做总览预警与单船解释增强。</li>
          <li>它更像在回答“这艘船和大多数船不一样在哪里”。</li>
        </ul>
      </div>
    </section>

    <section class="panel">
      <h2>六、哪些部分有真实机制支撑，哪些仍是启发式近似</h2>
      <div class="two-col">
        <div class="card">
          <h3>已有真实机制支撑</h3>
          <ul>
            <li>行为暴露是污损倾向主因。</li>
            <li>海温、盐度、生产力代理和水动力条件会影响附着窗口。</li>
            <li>流速应按 current_speed 理解，而不是把 u / v 分开单独打分。</li>
            <li>污损倾向升高后，潜在能耗和维护代价会被放大。</li>
            <li>短期时序模型适合做下一窗口风险预测。</li>
            <li>无监督异常检测适合做“偏离常规模式”的筛查。</li>
          </ul>
        </div>
        <div class="card">
          <h3>仍属启发式近似</h3>
          <ul>
            <li>各环境变量的具体分段切点。</li>
            <li>EnvModifier 与 RRI 的组合权重。</li>
            <li>CarbonPenaltyModifier 的具体系数。</li>
            <li>FPI、ECP 的分级阈值。</li>
            <li>异常分级阈值与异常类型规则。</li>
            <li>LSTM 风险标签阈值与 Autoencoder 分层阈值。</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="panel">
      <h2>七、这部分我们做了吗</h2>
      <div class="two-col">
        <div class="card">
          <h3>已经完成</h3>
          <ul>
            <li>环境因子区间响应重构。</li>
            <li>FPI / ECP / RRI 的结构性收口。</li>
            <li>科学性 review 文档。</li>
            <li>评分结构说明。</li>
            <li>参数来源表。</li>
            <li>新旧评分对比图。</li>
            <li>前端“核心算法”解释入口。</li>
          </ul>
        </div>
        <div class="card">
          <h3>尚未完全完成</h3>
          <ul>
            <li>逐项文献级标定。</li>
            <li>外部实测样本校准。</li>
            <li>ECP 与正式碳核算之间的外部映射。</li>
            <li>跨区域、跨季节稳定性验证。</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="panel">
      <h2>推荐答辩表述</h2>
      <ul>
        <li>FPI、ECP、RRI 是可解释代理指标，不是绝对真值。</li>
        <li>FPI 体现的是行为主导、环境修正、维护轻修正。</li>
        <li>ECP 体现的是潜在代价放大，不是正式碳核算。</li>
        <li>RRI 体现的是区域综合风险条件，不是真实污损地图。</li>
        <li>LSTM 用于短期趋势预测，异常检测用于异常筛查，两者都不替代规则主链路。</li>
      </ul>
    </section>
  </div>
</body>
</html>
"@

$html | Set-Content -Path $outputPath -Encoding utf8
Write-Output "Scientific statement HTML written to: $outputPath"
