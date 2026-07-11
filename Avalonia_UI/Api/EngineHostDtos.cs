using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Avalonia_UI.Api;

public sealed record HealthStatusDto
{
    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;
}

public sealed record NodePortDefinitionDto
{
    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("required")]
    public bool Required { get; init; }
}

public sealed record NodeTableInputSlotDto
{
    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("required")]
    public bool Required { get; init; }

    [JsonPropertyName("allowed_storage_kinds")]
    public string[] AllowedStorageKinds { get; init; } = [];

    [JsonPropertyName("display_name")]
    public string? DisplayName { get; init; }

    [JsonPropertyName("description")]
    public string? Description { get; init; }

    [JsonPropertyName("default_source")]
    public string? DefaultSource { get; init; }
}

public sealed record NodeTableOutputSlotDto
{
    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("default_role")]
    public string DefaultRole { get; init; } = string.Empty;

    [JsonPropertyName("allow_current")]
    public bool AllowCurrent { get; init; }

    [JsonPropertyName("allow_new_memory")]
    public bool AllowNewMemory { get; init; }

    [JsonPropertyName("allow_new_runtime_sql")]
    public bool AllowNewRuntimeSql { get; init; }

    [JsonPropertyName("allow_existing_memory")]
    public bool AllowExistingMemory { get; init; }

    [JsonPropertyName("allow_existing_runtime_sql")]
    public bool AllowExistingRuntimeSql { get; init; }

    [JsonPropertyName("display_name")]
    public string? DisplayName { get; init; }

    [JsonPropertyName("description")]
    public string? Description { get; init; }
}

public sealed record NodeDefinitionDto
{
    [JsonPropertyName("node_type")]
    public string NodeType { get; init; } = string.Empty;

    [JsonPropertyName("node_version")]
    public string NodeVersion { get; init; } = string.Empty;

    [JsonPropertyName("display_name")]
    public string DisplayName { get; init; } = string.Empty;

    [JsonPropertyName("input_ports")]
    public NodePortDefinitionDto[] InputPorts { get; init; } = [];

    [JsonPropertyName("output_ports")]
    public NodePortDefinitionDto[] OutputPorts { get; init; } = [];

    [JsonPropertyName("input_table_slots")]
    public NodeTableInputSlotDto[] InputTableSlots { get; init; } = [];

    [JsonPropertyName("output_table_slots")]
    public NodeTableOutputSlotDto[] OutputTableSlots { get; init; } = [];

    [JsonPropertyName("execution_mode")]
    public string ExecutionMode { get; init; } = string.Empty;

    [JsonPropertyName("default_timeout_seconds")]
    public int DefaultTimeoutSeconds { get; init; }

    [JsonPropertyName("retry_safe")]
    public bool RetrySafe { get; init; }

    [JsonPropertyName("ui_visibility")]
    public string UiVisibility { get; init; } = string.Empty;

    [JsonPropertyName("config_schema_version")]
    public string ConfigSchemaVersion { get; init; } = string.Empty;

    [JsonPropertyName("config_schema")]
    public JsonElement? ConfigSchema { get; init; }
}

public sealed record NodeDefinitionCatalogStateDto
{
    [JsonPropertyName("catalog_hash")]
    public string CatalogHash { get; init; } = string.Empty;

    [JsonPropertyName("node_count")]
    public int NodeCount { get; init; }

    [JsonPropertyName("program_hash")]
    public string? ProgramHash { get; init; }
}

public sealed record WorkflowDefinitionDto
{
    [JsonPropertyName("workflow_id")]
    public string WorkflowId { get; init; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("revision_id")]
    public string RevisionId { get; init; } = string.Empty;

    [JsonPropertyName("version")]
    public int Version { get; init; }

    [JsonPropertyName("definition_hash")]
    public string DefinitionHash { get; init; } = string.Empty;

    [JsonPropertyName("definition")]
    public JsonElement Definition { get; init; }

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; init; }

    [JsonPropertyName("updated_at")]
    public DateTimeOffset UpdatedAt { get; init; }
}

public sealed record WorkflowCreateRequestDto
{
    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("definition")]
    public JsonElement Definition { get; init; }
}

public sealed record WorkflowValidateRequestDto
{
    [JsonPropertyName("definition")]
    public JsonElement Definition { get; init; }
}

public sealed record WorkflowUpdateRequestDto
{
    [JsonPropertyName("name")]
    public string? Name { get; init; }

    [JsonPropertyName("definition")]
    public JsonElement Definition { get; init; }

    [JsonPropertyName("base_revision_id")]
    public string BaseRevisionId { get; init; } = string.Empty;
}

public sealed record WorkflowDeleteResultDto
{
    [JsonPropertyName("workflow_id")]
    public string WorkflowId { get; init; } = string.Empty;

    [JsonPropertyName("deleted")]
    public bool Deleted { get; init; }
}

public sealed record WorkflowValidationIssueDto
{
    [JsonPropertyName("code")]
    public string Code { get; init; } = string.Empty;

    [JsonPropertyName("path")]
    public string Path { get; init; } = string.Empty;

    [JsonPropertyName("message")]
    public string Message { get; init; } = string.Empty;
}

public sealed record WorkflowValidationResultDto
{
    [JsonPropertyName("valid")]
    public bool Valid { get; init; }

    [JsonPropertyName("errors")]
    public WorkflowValidationIssueDto[] Errors { get; init; } = [];

    [JsonPropertyName("warnings")]
    public WorkflowValidationIssueDto[] Warnings { get; init; } = [];
}

public sealed record WorkflowRevisionDto
{
    [JsonPropertyName("revision_id")]
    public string RevisionId { get; init; } = string.Empty;

    [JsonPropertyName("workflow_id")]
    public string WorkflowId { get; init; } = string.Empty;

    [JsonPropertyName("version")]
    public int Version { get; init; }

    [JsonPropertyName("definition_hash")]
    public string DefinitionHash { get; init; } = string.Empty;

    [JsonPropertyName("definition")]
    public JsonElement Definition { get; init; }

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; init; }

    [JsonPropertyName("created_by")]
    public string? CreatedBy { get; init; }
}

public sealed record WorkflowRunDto
{
    [JsonPropertyName("workflow_run_id")]
    public string WorkflowRunId { get; init; } = string.Empty;

    [JsonPropertyName("workflow_id")]
    public string WorkflowId { get; init; } = string.Empty;

    [JsonPropertyName("revision_id")]
    public string? RevisionId { get; init; }

    [JsonPropertyName("workflow_version")]
    public int WorkflowVersion { get; init; }

    [JsonPropertyName("definition_hash")]
    public string? DefinitionHash { get; init; }

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("run_mode")]
    public string RunMode { get; init; } = string.Empty;

    [JsonPropertyName("trigger_source")]
    public string TriggerSource { get; init; } = string.Empty;

    [JsonPropertyName("target_node_instance_id")]
    public string? TargetNodeInstanceId { get; init; }

    [JsonPropertyName("state_version")]
    public int StateVersion { get; init; }

    [JsonPropertyName("owner_process_id")]
    public string? OwnerProcessId { get; init; }

    [JsonPropertyName("process_generation")]
    public int ProcessGeneration { get; init; }

    [JsonPropertyName("fencing_token")]
    public string? FencingToken { get; init; }

    [JsonPropertyName("input_snapshot_id")]
    public string? InputSnapshotId { get; init; }

    [JsonPropertyName("started_at")]
    public DateTimeOffset? StartedAt { get; init; }

    [JsonPropertyName("finished_at")]
    public DateTimeOffset? FinishedAt { get; init; }

    [JsonPropertyName("completion_reason")]
    public string? CompletionReason { get; init; }

    [JsonPropertyName("error")]
    public JsonElement? Error { get; init; }
}

public sealed record RuntimeFeedbackTelemetryOverrideDto
{
    [JsonPropertyName("log_level")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? LogLevel { get; init; }

    [JsonPropertyName("event_level")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? EventLevel { get; init; }

    [JsonPropertyName("event_rate_limit_per_second")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? EventRateLimitPerSecond { get; init; }

    [JsonPropertyName("progress_enabled")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public bool? ProgressEnabled { get; init; }

    [JsonPropertyName("progress_interval_seconds")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public double? ProgressIntervalSeconds { get; init; }
}

public sealed record RuntimeFeedbackDiagnosticsOverrideDto
{
    [JsonPropertyName("capture_error_context")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public bool? CaptureErrorContext { get; init; }

    [JsonPropertyName("include_metrics")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public bool? IncludeMetrics { get; init; }

    [JsonPropertyName("payload_byte_limit")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? PayloadByteLimit { get; init; }

    [JsonPropertyName("redact_columns")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public List<string>? RedactColumns { get; init; }

    [JsonPropertyName("mask_policy")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? MaskPolicy { get; init; }
}

public sealed record RuntimeFeedbackPolicyOverrideDto
{
    [JsonPropertyName("telemetry")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public RuntimeFeedbackTelemetryOverrideDto? Telemetry { get; init; }

    [JsonPropertyName("diagnostics")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public RuntimeFeedbackDiagnosticsOverrideDto? Diagnostics { get; init; }
}

public sealed record WorkflowRunRuntimeOptionsOverlayDto
{
    [JsonPropertyName("workflow")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public RuntimeFeedbackPolicyOverrideDto? Workflow { get; init; }

    [JsonPropertyName("node_overrides")]
    public Dictionary<string, RuntimeFeedbackPolicyOverrideDto> NodeOverrides { get; init; } = new();
}

public sealed record ResolvedRuntimeFeedbackTelemetryDto
{
    [JsonPropertyName("log_level")]
    public string LogLevel { get; init; } = string.Empty;

    [JsonPropertyName("event_level")]
    public string EventLevel { get; init; } = string.Empty;

    [JsonPropertyName("event_rate_limit_per_second")]
    public int EventRateLimitPerSecond { get; init; }

    [JsonPropertyName("progress_enabled")]
    public bool ProgressEnabled { get; init; }

    [JsonPropertyName("progress_interval_seconds")]
    public double ProgressIntervalSeconds { get; init; }
}

public sealed record ResolvedRuntimeFeedbackDiagnosticsDto
{
    [JsonPropertyName("capture_error_context")]
    public bool CaptureErrorContext { get; init; }

    [JsonPropertyName("include_metrics")]
    public bool IncludeMetrics { get; init; }

    [JsonPropertyName("payload_byte_limit")]
    public int PayloadByteLimit { get; init; }

    [JsonPropertyName("redact_columns")]
    public List<string> RedactColumns { get; init; } = new();

    [JsonPropertyName("mask_policy")]
    public string MaskPolicy { get; init; } = string.Empty;
}

public sealed record ResolvedRuntimeFeedbackPolicyDto
{
    [JsonPropertyName("telemetry")]
    public ResolvedRuntimeFeedbackTelemetryDto Telemetry { get; init; } = new();

    [JsonPropertyName("diagnostics")]
    public ResolvedRuntimeFeedbackDiagnosticsDto Diagnostics { get; init; } = new();
}

public sealed record WorkflowRunRuntimeOptionsEffectiveSummaryDto
{
    [JsonPropertyName("workflow")]
    public ResolvedRuntimeFeedbackPolicyDto Workflow { get; init; } = new();

    [JsonPropertyName("nodes")]
    public Dictionary<string, ResolvedRuntimeFeedbackPolicyDto> Nodes { get; init; } = new();
}

public sealed record ActiveNodeTaskRuntimeOptionsVersionDto
{
    [JsonPropertyName("task_id")]
    public string TaskId { get; init; } = string.Empty;

    [JsonPropertyName("node_run_id")]
    public string NodeRunId { get; init; } = string.Empty;

    [JsonPropertyName("node_instance_id")]
    public string NodeInstanceId { get; init; } = string.Empty;

    [JsonPropertyName("node_run_status")]
    public string NodeRunStatus { get; init; } = string.Empty;

    [JsonPropertyName("runtime_options_version")]
    public int RuntimeOptionsVersion { get; init; }
}

public sealed record WorkflowRunRuntimeOptionsDto
{
    [JsonPropertyName("workflow_run_id")]
    public string WorkflowRunId { get; init; } = string.Empty;

    [JsonPropertyName("saved_runtime_options")]
    public JsonElement SavedRuntimeOptions { get; init; }

    [JsonPropertyName("overlay")]
    public WorkflowRunRuntimeOptionsOverlayDto Overlay { get; init; } = new();

    [JsonPropertyName("effective_summary")]
    public WorkflowRunRuntimeOptionsEffectiveSummaryDto EffectiveSummary { get; init; } = new();

    [JsonPropertyName("requested_version")]
    public int RequestedVersion { get; init; }

    [JsonPropertyName("applied_version")]
    public int AppliedVersion { get; init; }

    [JsonPropertyName("requested_at")]
    public DateTimeOffset? RequestedAt { get; init; }

    [JsonPropertyName("applied_at")]
    public DateTimeOffset? AppliedAt { get; init; }

    [JsonPropertyName("active_task_versions")]
    public List<ActiveNodeTaskRuntimeOptionsVersionDto> ActiveTaskVersions { get; init; } = new();
}

public sealed record WorkflowRunRuntimeOptionsUpdateRequestDto
{
    [JsonPropertyName("expected_version")]
    public int ExpectedVersion { get; init; }

    [JsonPropertyName("overlay")]
    public WorkflowRunRuntimeOptionsOverlayDto Overlay { get; init; } = new();
}

public sealed record WorkflowProcessDto
{
    [JsonPropertyName("process_id")]
    public string ProcessId { get; init; } = string.Empty;

    [JsonPropertyName("workflow_run_id")]
    public string WorkflowRunId { get; init; } = string.Empty;

    [JsonPropertyName("os_pid")]
    public int? OsPid { get; init; }

    [JsonPropertyName("process_generation")]
    public int ProcessGeneration { get; init; }

    [JsonPropertyName("fencing_token")]
    public string? FencingToken { get; init; }

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("started_at")]
    public DateTimeOffset StartedAt { get; init; }

    [JsonPropertyName("last_heartbeat_at")]
    public DateTimeOffset? LastHeartbeatAt { get; init; }

    [JsonPropertyName("cancel_requested_at")]
    public DateTimeOffset? CancelRequestedAt { get; init; }

    [JsonPropertyName("exited_at")]
    public DateTimeOffset? ExitedAt { get; init; }

    [JsonPropertyName("exit_code")]
    public int? ExitCode { get; init; }

    [JsonPropertyName("error")]
    public JsonElement? Error { get; init; }
}

public sealed record NodeRunDto
{
    [JsonPropertyName("node_run_id")]
    public string NodeRunId { get; init; } = string.Empty;

    [JsonPropertyName("workflow_run_id")]
    public string WorkflowRunId { get; init; } = string.Empty;

    [JsonPropertyName("node_instance_id")]
    public string NodeInstanceId { get; init; } = string.Empty;

    [JsonPropertyName("node_type")]
    public string NodeType { get; init; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("state_version")]
    public int StateVersion { get; init; }

    [JsonPropertyName("executor_id")]
    public string? ExecutorId { get; init; }

    [JsonPropertyName("progress")]
    public double? Progress { get; init; }

    [JsonPropertyName("current_stage")]
    public string? CurrentStage { get; init; }

    [JsonPropertyName("attempt")]
    public int Attempt { get; init; }

    [JsonPropertyName("started_at")]
    public DateTimeOffset? StartedAt { get; init; }

    [JsonPropertyName("finished_at")]
    public DateTimeOffset? FinishedAt { get; init; }

    [JsonPropertyName("last_heartbeat")]
    public DateTimeOffset? LastHeartbeat { get; init; }

    [JsonPropertyName("error")]
    public JsonElement? Error { get; init; }
}

public sealed record NodeRunPageDto
{
    [JsonPropertyName("items")]
    public NodeRunDto[] Items { get; init; } = [];

    [JsonPropertyName("offset")]
    public int Offset { get; init; }

    [JsonPropertyName("limit")]
    public int Limit { get; init; }

    [JsonPropertyName("total")]
    public int Total { get; init; }

    [JsonPropertyName("has_more")]
    public bool HasMore { get; init; }
}

public sealed record LoopRunDto
{
    [JsonPropertyName("loop_run_id")]
    public string LoopRunId { get; init; } = string.Empty;

    [JsonPropertyName("workflow_run_id")]
    public string WorkflowRunId { get; init; } = string.Empty;

    [JsonPropertyName("loop_id")]
    public string LoopId { get; init; } = string.Empty;

    [JsonPropertyName("start_node_instance_id")]
    public string StartNodeInstanceId { get; init; } = string.Empty;

    [JsonPropertyName("judge_node_instance_id")]
    public string JudgeNodeInstanceId { get; init; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("state_version")]
    public int StateVersion { get; init; }

    [JsonPropertyName("current_iteration")]
    public int CurrentIteration { get; init; }

    [JsonPropertyName("max_iterations")]
    public int MaxIterations { get; init; }

    [JsonPropertyName("exit_reason")]
    public string? ExitReason { get; init; }

    [JsonPropertyName("started_at")]
    public DateTimeOffset? StartedAt { get; init; }

    [JsonPropertyName("finished_at")]
    public DateTimeOffset? FinishedAt { get; init; }

    [JsonPropertyName("error")]
    public JsonElement? Error { get; init; }

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; init; }
}

public sealed record LoopIterationRunDto
{
    [JsonPropertyName("loop_iteration_id")]
    public string LoopIterationId { get; init; } = string.Empty;

    [JsonPropertyName("loop_run_id")]
    public string LoopRunId { get; init; } = string.Empty;

    [JsonPropertyName("iteration_index")]
    public int IterationIndex { get; init; }

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("state_version")]
    public int StateVersion { get; init; }

    [JsonPropertyName("input_table_ref_id")]
    public string? InputTableRefId { get; init; }

    [JsonPropertyName("input_selector")]
    public JsonElement? InputSelector { get; init; }

    [JsonPropertyName("output_table_ref_id")]
    public string? OutputTableRefId { get; init; }

    [JsonPropertyName("failed_node_run_id")]
    public string? FailedNodeRunId { get; init; }

    [JsonPropertyName("started_at")]
    public DateTimeOffset? StartedAt { get; init; }

    [JsonPropertyName("finished_at")]
    public DateTimeOffset? FinishedAt { get; init; }

    [JsonPropertyName("error")]
    public JsonElement? Error { get; init; }

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; init; }
}

public sealed record LoopIterationNodeRunDto
{
    [JsonPropertyName("loop_iteration_id")]
    public string LoopIterationId { get; init; } = string.Empty;

    [JsonPropertyName("node_run_id")]
    public string NodeRunId { get; init; } = string.Empty;

    [JsonPropertyName("node_instance_id")]
    public string NodeInstanceId { get; init; } = string.Empty;

    [JsonPropertyName("role")]
    public string Role { get; init; } = string.Empty;

    [JsonPropertyName("node_type")]
    public string NodeType { get; init; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("progress")]
    public double? Progress { get; init; }

    [JsonPropertyName("current_stage")]
    public string? CurrentStage { get; init; }

    [JsonPropertyName("attempt")]
    public int Attempt { get; init; }

    [JsonPropertyName("started_at")]
    public DateTimeOffset? StartedAt { get; init; }

    [JsonPropertyName("finished_at")]
    public DateTimeOffset? FinishedAt { get; init; }

    [JsonPropertyName("error")]
    public JsonElement? Error { get; init; }
}

public sealed record LoopIterationTableRefDto
{
    [JsonPropertyName("loop_iteration_id")]
    public string LoopIterationId { get; init; } = string.Empty;

    [JsonPropertyName("table_ref_id")]
    public string TableRefId { get; init; } = string.Empty;

    [JsonPropertyName("role")]
    public string Role { get; init; } = string.Empty;

    [JsonPropertyName("logical_table_id")]
    public string? LogicalTableId { get; init; }

    [JsonPropertyName("storage_kind")]
    public string? StorageKind { get; init; }

    [JsonPropertyName("table_role")]
    public string? TableRole { get; init; }

    [JsonPropertyName("version")]
    public int? Version { get; init; }

    [JsonPropertyName("lifecycle_status")]
    public string? LifecycleStatus { get; init; }

    [JsonPropertyName("source_node_run_id")]
    public string? SourceNodeRunId { get; init; }

    [JsonPropertyName("source_node_instance_id")]
    public string? SourceNodeInstanceId { get; init; }

    [JsonPropertyName("output_slot")]
    public string? OutputSlot { get; init; }

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; init; }
}

public sealed record RuntimeEventDto
{
    [JsonPropertyName("event_id")]
    public string EventId { get; init; } = string.Empty;

    [JsonPropertyName("sequence_number")]
    public long SequenceNumber { get; init; }

    [JsonPropertyName("event_version")]
    public string EventVersion { get; init; } = string.Empty;

    [JsonPropertyName("event_type")]
    public string EventType { get; init; } = string.Empty;

    [JsonPropertyName("timestamp")]
    public DateTimeOffset Timestamp { get; init; }

    [JsonPropertyName("workflow_run_id")]
    public string? WorkflowRunId { get; init; }

    [JsonPropertyName("node_run_id")]
    public string? NodeRunId { get; init; }

    [JsonPropertyName("payload")]
    public JsonElement Payload { get; init; }
}

public sealed record TableRefDto
{
    [JsonPropertyName("table_ref_id")]
    public string TableRefId { get; init; } = string.Empty;

    [JsonPropertyName("workflow_run_id")]
    public string WorkflowRunId { get; init; } = string.Empty;

    [JsonPropertyName("node_run_id")]
    public string NodeRunId { get; init; } = string.Empty;

    [JsonPropertyName("source_node_run_id")]
    public string? SourceNodeRunId { get; init; }

    [JsonPropertyName("source_node_instance_id")]
    public string? SourceNodeInstanceId { get; init; }

    [JsonPropertyName("role")]
    public string Role { get; init; } = string.Empty;

    [JsonPropertyName("storage_kind")]
    public string StorageKind { get; init; } = string.Empty;

    [JsonPropertyName("scope")]
    public string Scope { get; init; } = string.Empty;

    [JsonPropertyName("mutability")]
    public string Mutability { get; init; } = string.Empty;

    [JsonPropertyName("provider_id")]
    public string ProviderId { get; init; } = string.Empty;

    [JsonPropertyName("resource_profile_id")]
    public string? ResourceProfileId { get; init; }

    [JsonPropertyName("mount_id")]
    public string? MountId { get; init; }

    [JsonPropertyName("logical_table_id")]
    public string LogicalTableId { get; init; } = string.Empty;

    [JsonPropertyName("output_slot")]
    public string? OutputSlot { get; init; }

    [JsonPropertyName("table_type")]
    public string TableType { get; init; } = string.Empty;

    [JsonPropertyName("preview_persistence")]
    public string PreviewPersistence { get; init; } = string.Empty;

    [JsonPropertyName("can_read_rows")]
    public bool CanReadRows { get; init; }

    [JsonPropertyName("supports_paged_rows")]
    public bool SupportsPagedRows { get; init; }

    [JsonPropertyName("schema")]
    public JsonElement? Schema { get; init; }

    [JsonPropertyName("schema_fingerprint")]
    public string SchemaFingerprint { get; init; } = string.Empty;

    [JsonPropertyName("version")]
    public int Version { get; init; }

    [JsonPropertyName("capabilities")]
    public string[] Capabilities { get; init; } = [];

    [JsonPropertyName("lifecycle_status")]
    public string LifecycleStatus { get; init; } = string.Empty;

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; init; }
}

public sealed record RunTableDirectoryPageDto
{
    [JsonPropertyName("items")]
    public TableRefDto[] Items { get; init; } = [];

    [JsonPropertyName("offset")]
    public int Offset { get; init; }

    [JsonPropertyName("limit")]
    public int Limit { get; init; }

    [JsonPropertyName("total")]
    public int Total { get; init; }

    [JsonPropertyName("has_more")]
    public bool HasMore { get; init; }
}

public sealed record RunTableCleanupIssueDto
{
    [JsonPropertyName("table_ref_id")]
    public string TableRefId { get; init; } = string.Empty;

    [JsonPropertyName("reason")]
    public string Reason { get; init; } = string.Empty;
}

public sealed record RunTableCleanupResultDto
{
    [JsonPropertyName("workflow_run_id")]
    public string WorkflowRunId { get; init; } = string.Empty;

    [JsonPropertyName("cleaned_count")]
    public int CleanedCount { get; init; }

    [JsonPropertyName("skipped_count")]
    public int SkippedCount { get; init; }

    [JsonPropertyName("failed_count")]
    public int FailedCount { get; init; }

    [JsonPropertyName("cleaned_table_refs")]
    public TableRefDto[] CleanedTableRefs { get; init; } = [];

    [JsonPropertyName("skipped")]
    public RunTableCleanupIssueDto[] Skipped { get; init; } = [];

    [JsonPropertyName("failed")]
    public RunTableCleanupIssueDto[] Failed { get; init; } = [];
}

public sealed record TableFieldSchemaDto
{
    [JsonPropertyName("field_id")]
    public string FieldId { get; init; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("data_type")]
    public string DataType { get; init; } = string.Empty;

    [JsonPropertyName("nullable")]
    public bool Nullable { get; init; }

    [JsonPropertyName("ordinal")]
    public int Ordinal { get; init; }
}

public sealed record TableDataSchemaDto
{
    [JsonPropertyName("table_ref_id")]
    public string TableRefId { get; init; } = string.Empty;

    [JsonPropertyName("schema")]
    public TableFieldSchemaDto[] Schema { get; init; } = [];

    [JsonPropertyName("schema_fingerprint")]
    public string SchemaFingerprint { get; init; } = string.Empty;
}

public sealed record TableDataSummaryDto
{
    [JsonPropertyName("table_ref_id")]
    public string TableRefId { get; init; } = string.Empty;

    [JsonPropertyName("workflow_run_id")]
    public string WorkflowRunId { get; init; } = string.Empty;

    [JsonPropertyName("node_run_id")]
    public string NodeRunId { get; init; } = string.Empty;

    [JsonPropertyName("logical_table_id")]
    public string LogicalTableId { get; init; } = string.Empty;

    [JsonPropertyName("storage_kind")]
    public string StorageKind { get; init; } = string.Empty;

    [JsonPropertyName("lifecycle_status")]
    public string LifecycleStatus { get; init; } = string.Empty;

    [JsonPropertyName("version")]
    public int Version { get; init; }

    [JsonPropertyName("schema_fingerprint")]
    public string SchemaFingerprint { get; init; } = string.Empty;

    [JsonPropertyName("capabilities")]
    public string[] Capabilities { get; init; } = [];

    [JsonPropertyName("row_count")]
    public long RowCount { get; init; }
}

public sealed record TableDataRowsDto
{
    [JsonPropertyName("table_ref_id")]
    public string TableRefId { get; init; } = string.Empty;

    [JsonPropertyName("offset")]
    public int Offset { get; init; }

    [JsonPropertyName("limit")]
    public int Limit { get; init; }

    [JsonPropertyName("row_count")]
    public long RowCount { get; init; }

    [JsonPropertyName("columns")]
    public string[] Columns { get; init; } = [];

    [JsonPropertyName("rows")]
    public JsonElement[] Rows { get; init; } = [];

    [JsonPropertyName("has_more")]
    public bool HasMore { get; init; }
}

public sealed record SharedPublicationDto
{
    [JsonPropertyName("publication_id")]
    public string PublicationId { get; init; } = string.Empty;

    [JsonPropertyName("share_name")]
    public string ShareName { get; init; } = string.Empty;

    [JsonPropertyName("publication_version")]
    public int PublicationVersion { get; init; }

    [JsonPropertyName("producer_workflow_id")]
    public string ProducerWorkflowId { get; init; } = string.Empty;

    [JsonPropertyName("producer_run_id")]
    public string ProducerRunId { get; init; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("input_snapshot_id")]
    public string? InputSnapshotId { get; init; }

    [JsonPropertyName("retention_policy")]
    public JsonElement? RetentionPolicy { get; init; }

    [JsonPropertyName("created_at")]
    public DateTimeOffset CreatedAt { get; init; }

    [JsonPropertyName("members")]
    public SharedPublicationMemberDto[] Members { get; init; } = [];
}

public sealed record SharedPublicationMemberDto
{
    [JsonPropertyName("publication_id")]
    public string PublicationId { get; init; } = string.Empty;

    [JsonPropertyName("export_name")]
    public string ExportName { get; init; } = string.Empty;

    [JsonPropertyName("table_ref_id")]
    public string TableRefId { get; init; } = string.Empty;

    [JsonPropertyName("exact_table_version")]
    public int ExactTableVersion { get; init; }
}
