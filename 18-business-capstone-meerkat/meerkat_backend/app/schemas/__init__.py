from pydantic import BaseModel, ConfigDict, Field


class SimulationComment(BaseModel):
    user_name: str = "anonymous"
    body: str
    external_message_id: str | None = None
    user_external_id: str | None = None


class SimulationRequest(BaseModel):
    session_id: int = 1
    comments: list[SimulationComment] = Field(default_factory=list)


class SimulationResponse(BaseModel):
    inserted: int
    agent_runs_triggered: int
    alerts_created: int
    trace_id: str | None = None
    agent_run_id: int | None = None


class StreamHealthSampleInput(BaseModel):
    is_live: bool = True
    video_present: bool = True
    audio_present: bool = True
    bitrate_kbps: int | None = None
    fps: float | None = None
    width: int | None = None
    height: int | None = None
    last_segment_age_ms: int | None = None
    probe_status: str = "OK"
    probe_error: str | None = None


class StreamHealthSimulationRequest(BaseModel):
    session_id: int = 1
    scenario: str = "stream_down"
    samples: list[StreamHealthSampleInput] = Field(default_factory=list)


class StreamProbeRunOnceRequest(BaseModel):
    session_id: int = 1
    owncast_base_url: str | None = None
    hls_playlist_url: str | None = None


class PostLiveReportRequest(BaseModel):
    session_id: int = 1


class CreateLiveSessionRequest(BaseModel):
    title: str


class CreateOpsAlertRequest(BaseModel):
    session_id: int
    alert_type: str
    severity: str
    title: str
    summary: str
    evidence: dict
    product_id: int | None = None
    coupon_id: int | None = None
    trace_id: str | None = None


class CreateSpeakerNoteRequest(BaseModel):
    session_id: int
    body: str
    target: str = "anchor"
    alert_id: int | None = None
    trace_id: str | None = None


class CreateApprovalTaskRequest(BaseModel):
    session_id: int
    title: str
    reason: str
    payload: dict
    risk_level: str
    proposal_id: int | None = None
    trace_id: str | None = None


class CreateActionProposalRequest(BaseModel):
    session_id: int
    action_type: str
    risk_level: str
    arguments: dict
    reason: str
    status: str = "PROPOSED"
    alert_id: int | None = None
    created_by_agent: str = "commander"
    trace_id: str | None = None


class CreateAgentTaskRequest(BaseModel):
    session_id: int
    source: str = "manual"
    alert_type_hint: str | None = None
    comment_ids: list[int] = Field(default_factory=list)
    input_payload: dict = Field(default_factory=dict)


class PublicModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
