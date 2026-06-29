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

    [JsonPropertyName("execution_mode")]
    public string ExecutionMode { get; init; } = string.Empty;

    [JsonPropertyName("default_timeout_seconds")]
    public int DefaultTimeoutSeconds { get; init; }

    [JsonPropertyName("retry_safe")]
    public bool RetrySafe { get; init; }

    [JsonPropertyName("ui_visibility")]
    public string UiVisibility { get; init; } = string.Empty;
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

    [JsonPropertyName("logical_table_id")]
    public string LogicalTableId { get; init; } = string.Empty;

    [JsonPropertyName("schema")]
    public JsonElement Schema { get; init; }

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

public sealed record AuditEventDto
{
    [JsonPropertyName("audit_event_id")]
    public string AuditEventId { get; init; } = string.Empty;

    [JsonPropertyName("event_type")]
    public string EventType { get; init; } = string.Empty;

    [JsonPropertyName("decision")]
    public string Decision { get; init; } = string.Empty;

    [JsonPropertyName("workflow_run_id")]
    public string? WorkflowRunId { get; init; }

    [JsonPropertyName("node_run_id")]
    public string? NodeRunId { get; init; }

    [JsonExtensionData]
    public IDictionary<string, JsonElement> ExtensionData { get; init; } =
        new Dictionary<string, JsonElement>();
}
