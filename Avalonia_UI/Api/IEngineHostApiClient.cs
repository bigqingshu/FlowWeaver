using System;
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

    Task<ApiResponseEnvelope<WorkflowValidationResultDto>> ValidateWorkflowDraftAsync(
        EngineHostConnectionSettings settings,
        JsonElement definition,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowDefinitionDto>> UpdateWorkflowAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string? name,
        JsonElement definition,
        string baseRevisionId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowDefinitionDto>> GetWorkflowAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowDeleteResultDto>> DeleteWorkflowAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        CancellationToken cancellationToken = default)
    {
        throw new NotSupportedException("Workflow delete API is not implemented.");
    }

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

    Task<ApiResponseEnvelope<WorkflowRunDto>> StartWorkflowRunAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string runMode,
        string? targetNodeInstanceId = null,
        CancellationToken cancellationToken = default)
    {
        return StartWorkflowRunAsync(settings, workflowId, cancellationToken);
    }

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

    Task<ApiResponseEnvelope<TableDataSchemaDto>> GetTableDataSchemaAsync(
        EngineHostConnectionSettings settings,
        string tableRefId,
        CancellationToken cancellationToken = default)
    {
        throw new NotSupportedException("Table data schema API is not implemented.");
    }

    Task<ApiResponseEnvelope<TableDataSummaryDto>> GetTableDataSummaryAsync(
        EngineHostConnectionSettings settings,
        string tableRefId,
        CancellationToken cancellationToken = default)
    {
        throw new NotSupportedException("Table data summary API is not implemented.");
    }

    Task<ApiResponseEnvelope<TableDataRowsDto>> GetTableDataRowsAsync(
        EngineHostConnectionSettings settings,
        string tableRefId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? columns = null,
        IReadOnlyCollection<string>? orderBy = null,
        CancellationToken cancellationToken = default)
    {
        throw new NotSupportedException("Table data rows API is not implemented.");
    }

    Task<ApiResponseEnvelope<List<RuntimeEventDto>>> ListEventsAsync(
        EngineHostConnectionSettings settings,
        long? afterSequenceNumber = null,
        string? workflowRunId = null,
        string? nodeRunId = null,
        string? eventType = null,
        int limit = 100,
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
