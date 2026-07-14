using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public interface IBackgroundRunService
{
    Task<ApiResponseEnvelope<WorkflowRunDto>> StartAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string runMode = "full",
        string? targetNodeInstanceId = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsAsync(
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

    Task<ApiResponseEnvelope<WorkflowRunDeleteResultDto>> DeleteAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowProcessDto>> CancelAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<WorkflowRunDto>> RetryAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string? triggerSource = null,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<RunTableCleanupResultDto>> CleanupTablesAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default);

    Task<ApiResponseEnvelope<RunTableCleanupResultDto>> CleanupTablesBatchAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        int maxRefs,
        int timeBudgetMs,
        string? cursor = null,
        CancellationToken cancellationToken = default)
    {
        return CleanupTablesAsync(settings, workflowRunId, cancellationToken);
    }
}
