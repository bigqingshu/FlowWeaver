using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.Services;

public sealed class BackgroundRunService : IBackgroundRunService
{
    private readonly IEngineHostApiClient _apiClient;

    public BackgroundRunService(IEngineHostApiClient apiClient)
    {
        _apiClient = apiClient;
    }

    public Task<ApiResponseEnvelope<WorkflowRunDto>> StartAsync(
        EngineHostConnectionSettings settings,
        string workflowId,
        string runMode = "full",
        string? targetNodeInstanceId = null,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.StartBackgroundWorkflowRunAsync(
            settings,
            workflowId,
            runMode,
            targetNodeInstanceId,
            cancellationToken);
    }

    public Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsAsync(
        EngineHostConnectionSettings settings,
        string? workflowId = null,
        IReadOnlyCollection<string>? statuses = null,
        string? runMode = null,
        string? triggerSource = null,
        int offset = 0,
        int limit = 100,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.ListRunsPageAsync(
            settings,
            workflowId,
            statuses,
            runMode,
            triggerSource,
            offset,
            limit,
            cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRunDto>> GetRunAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.GetRunAsync(settings, workflowRunId, cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowProcessDto>> CancelAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.CancelRunAsync(settings, workflowRunId, cancellationToken);
    }

    public Task<ApiResponseEnvelope<WorkflowRunDto>> RetryAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        string? triggerSource = null,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.RetryWorkflowRunAsync(
            settings,
            workflowRunId,
            triggerSource,
            cancellationToken);
    }

    public Task<ApiResponseEnvelope<RunTableCleanupResultDto>> CleanupTablesAsync(
        EngineHostConnectionSettings settings,
        string workflowRunId,
        CancellationToken cancellationToken = default)
    {
        return _apiClient.CleanupRunTableRefsAsync(
            settings,
            workflowRunId,
            cancellationToken);
    }
}
