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

    Task<ApiResponseEnvelope<NodeDefinitionCatalogStateDto>> GetNodeDefinitionCatalogStateAsync(
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

    Task<ApiResponseEnvelope<WorkflowRunDto>> StartWorkflowRunAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string runMode,
        string? targetNodeInstanceId = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowRunDto>> StartBackgroundWorkflowRunAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string runMode = "full",
        string? targetNodeInstanceId = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsAsync(
        EngineHostConnectionSettings settings,
        string? workflowId = null,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsPageAsync(
        EngineHostConnectionSettings settings,
        string? workflowId = null,
        IReadOnlyCollection<string>? statuses = null,
        string? runMode = null,
        string? triggerSource = null,
        int offset = 0,
        int limit = 100,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowRunDto>> GetRunAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> GetRunRuntimeOptionsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> ReplaceRunRuntimeOptionsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int expectedVersion,
        WorkflowRunRuntimeOptionsOverlayDto overlay,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<NodeRunPageDto>> ListNodeRunsPageAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 100,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowProcessDto>> CancelRunAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<TableRefDto>>> ListTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<RunTableDirectoryPageDto>> ListRunTableDirectoryAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 100,
        string? nodeRunId = null,
        string? tableType = null,
        IReadOnlyCollection<string>? lifecycleStatuses = null,
        string? logicalTableId = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<LoopRunDto>>> ListLoopRunsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<LoopIterationRunDto>>> ListLoopIterationsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? statuses = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<LoopIterationNodeRunDto>>> ListLoopIterationNodeRunsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<LoopIterationTableRefDto>>> ListLoopIterationTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string loopRunId,
        string loopIterationId,
        string? role = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowRunDto>> RetryWorkflowRunAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string? triggerSource = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<RunTableCleanupResultDto>> CleanupRunTableRefsAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<TableDataSchemaDto>> GetTableDataSchemaAsync(
        EngineHostConnectionSettings settings,
        string tableRefId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<TableDataSummaryDto>> GetTableDataSummaryAsync(
        EngineHostConnectionSettings settings,
        string tableRefId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<TableDataRowsDto>> GetTableDataRowsAsync(
        EngineHostConnectionSettings settings,
        string tableRefId,
        int offset = 0,
        int limit = 50,
        IReadOnlyCollection<string>? columns = null,
        IReadOnlyCollection<string>? orderBy = null,
        CancellationToken cancellationToken = default);

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
