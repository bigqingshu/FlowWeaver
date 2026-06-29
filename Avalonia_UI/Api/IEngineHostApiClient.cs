using System.Collections.Generic;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.Api;

public interface IEngineHostApiClient
{
    Task<ApiResponseEnvelope<HealthStatusDto>> GetHealthAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<NodeDefinitionDto>>> ListNodeDefinitionsAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<WorkflowDefinitionDto>>> ListWorkflowsAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowDefinitionDto>> CreateWorkflowAsync(
        EngineHostConnectionSettings settings,
        string name,
        JsonElement definition,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowDefinitionDto>> GetWorkflowAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<WorkflowRevisionDto>>> ListWorkflowRevisionsAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowRevisionDto>> GetWorkflowRevisionAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string revisionId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowRunDto>> StartWorkflowRunAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsAsync(
        EngineHostConnectionSettings settings,
        string? workflowId = null,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowProcessDto>> CancelRunAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<TableRefDto>>> ListTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<RuntimeEventDto>>> ListEventsAsync(
        EngineHostConnectionSettings settings,
        long? afterSequenceNumber = null,
        string? workflowRunId = null,
        string? nodeRunId = null,
        string? eventType = null,
        int limit = 100,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<AuditEventDto>>> ListAuditEventsAsync(
        EngineHostConnectionSettings settings,
        string? workflowRunId = null,
        string? nodeRunId = null,
        string? eventType = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<SharedPublicationDto>>> ListSharedPublicationsAsync(
        EngineHostConnectionSettings settings,
        string? shareName = null,
        int limit = 100,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<SharedPublicationDto>>> ListSharedPublicationVersionsAsync(
        EngineHostConnectionSettings settings,
        string shareName,
        int limit = 100,
        CancellationToken cancellationToken = default);
}
