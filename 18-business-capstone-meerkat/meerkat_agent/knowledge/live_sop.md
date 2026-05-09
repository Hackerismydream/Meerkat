# 直播运营 SOP

- 评论窗口达到异常阈值后，由 commander agent 接管。
- triage agent 先确认异常类型，业务 agent 查询证据，policy agent 检索规则，risk agent 判断动作风险，script agent 输出主播话术。
- 所有业务写入必须通过 Agent tools，并写入 trace。
