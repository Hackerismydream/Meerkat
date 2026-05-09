# 推流健康异常 SOP

## 断流 / STREAM_INTERRUPTED

当直播场次仍处于 LIVE 状态，但 HLS probe 连续失败或 Owncast 收到 STREAM_STOPPED 时，先创建 P1 运营告警。场控确认 OBS 是否断开，主播暂停商品讲解，避免在信号不可见时继续承诺价格、优惠券或库存。

## 无声 / NO_AUDIO

ffprobe 或 mock probe 发现音频轨缺失时，场控先检查麦克风、声卡和 OBS 音频源。主播话术只提示“声音正在确认”，不得承诺补偿。

## 分片停更 / SEGMENT_STALLED

HLS segment 长时间未更新时，按直播卡顿处理。连续异常需要升级告警，并记录 last_segment_age_ms 作为证据。
